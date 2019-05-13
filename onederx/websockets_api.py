import time
import json
import hmac
import base64
import hashlib
import asyncio
import websockets

from decimal import Decimal

DEBUG = False

class OnederxWebsockets:
    def __init__(self, user_callback, base_url, api_key=None, secret=None):
        self.user_callback = user_callback
        self.base_url = base_url
        self.api_key = api_key
        self.secret = secret
        self.cl_req_id_num = 0
        self.msg_queue = asyncio.Queue()
        self.callbacks_map = {}

    def _get_req_id(self):
        self.cl_req_id_num += 1
        return self.cl_req_id_num

    def _send(self, _type, payload=None, use_cl_req=False):
        msg = {"type": _type}
        cl_req_id = self._get_req_id()
        if payload is not None:
            if use_cl_req:
                payload["cl_req_id"] = cl_req_id
            msg["payload"] = payload
        self.msg_queue.put_nowait(json.dumps(msg))
        return cl_req_id

    def _subscribe(self, callback, channel, **kwargs):
        payload = {"channel": channel}
        payload["params"] = kwargs
        key = (channel, frozenset(payload["params"].items()))
        self.callbacks_map[key] = callback
        return self._send("subscribe", payload={"subscriptions":[payload]})

    def _get_callback(self, channel, params):
        if params is None:
            params = {}
        key = (channel, frozenset(params.items()))
        return self.callbacks_map.get(key, None)


    def auth(self):
        def _unix_nanosec():
            return int(time.time() * 1e9)

        def _signature_payload_onederx(url, payload_str):
            string_to_sign = url + payload_str
            signature = hmac.new(self.secret.encode(), msg=string_to_sign.encode(), digestmod=hashlib.sha512).hexdigest()
            return signature

        timestamp = str(_unix_nanosec())
        signature = _signature_payload_onederx("/v1/ws", timestamp)

        payload = {
            "api_key": self.api_key,
            "signature": signature,
            "timestamp": timestamp
        }   
        
        return self._send("auth", payload)

    def deauth(self):
        return self._send("deauth")

    def get_symbol_details(self):
        return self._send("symbol_details")

    def new_order(self, symbol, my_id, side, price, volume, order_type, time_in_force=None, is_post_only=False, is_stop=False):
        to_str = lambda x: str(Decimal(x))
        payload = {
            "symbol": symbol,
            "volume": to_str(volume),
            "price": to_str(price),
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
            "post_only": is_post_only,
            "stop": is_stop,
            "cl_ord_id": str(my_id)
        }

        if order_type == "limit":
            if time_in_force is None:
                raise ValueError("time_in_force must be set for orders with order_type='limit'")
        elif order_type == "market":
            if time_in_force is not None:
                raise ValueError("time_in_force must be None for orders with order_type='market'")
        return self._send("order_new", payload, use_cl_req=True)

    def cancel_order(self, symbol, order_id):
        payload = {"symbol": symbol, "order_id": order_id}
        return self._send("order_cancel", payload, use_cl_req=True)

    def cancel_all_orders(self, symbol):
        return self._send("order_cancel_all", {"symbol": symbol}, use_cl_req=True)

    def cancel_all_stop_orders(self, symbol):
        return self._send("order_cancel_all_stop", {"symbol": symbol}, use_cl_req=True)

    ### Subscribe to public ###

    def subscribe_l2(self, callback, symbol):
        return self._subscribe(callback, "l2", symbol=symbol)

    def subscribe_l3(self, callback, symbol):
        return self._subscribe(callback, "l3", symbol=symbol)

    def subscribe_trades(self, callback, symbol):
        return self._subscribe(callback, "trades", symbol=symbol)

    def subscribe_ticker(self, callback, symbol):
        return self._subscribe(callback, "ticker", symbol=symbol)

    def subscribe_candles(self, callback, symbol, resolution):
        return self._subscribe(callback, "candles", symbol=symbol, resolution=resolution)

    def subscribe_index(self, callback, name):
        return self._subscribe(callback, "index", name=name)

    ### Subscribe to private ###

    def subscribe_trades_private(self, callback, symbol):
        return self._subscribe(callback, "trades_private", symbol=symbol)

    def subscribe_l3_private(self, callback, symbol):
        return self._subscribe(callback, "l3_private", symbol=symbol)

    def subscribe_action_replies(self, callback, symbol):
        return self._subscribe(callback, "action_replies", symbol=symbol)

    def subscribe_stop_orders(self, callback, symbol):
        return self._subscribe(callback, "stop_orders", symbol=symbol)

    def subscribe_balances(self, callback):
        return self._subscribe(callback, "balances")

    def subscribe_positions(self, callback):
        return self._subscribe(callback, "positions")

    ### Async WS ###

    async def _run_websocket(self):
        async def read_loop(ws):
            while True:
                msg = await ws.recv()
                msg = json.loads(msg)
                self._callback(msg)

        async def send_loop(ws):   
            while True:
                msg_to_sent = await self.msg_queue.get()
                if DEBUG:
                    print("SENDING:", msg_to_sent)
                await ws.send(msg_to_sent)

        # TODO -- handle errors better
        try:
            async with websockets.connect(self.base_url + "/v1/ws", max_size=2**28) as ws:
                await asyncio.gather(read_loop(ws), send_loop(ws))
        except:
            import traceback
            traceback.print_exc()
            raise

    # Please use this function only for testing. The right way is to use `run_async` async method.
    def run_in_thread(self):
        import threading

        def forever():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            asyncio.get_event_loop().run_until_complete(self.run_async())

        t = threading.Thread(target=forever, args=())
        t.start()

    async def run_async(self):
        tasks = asyncio.wait([self._run_websocket()], return_when=asyncio.FIRST_EXCEPTION)
        await tasks

    def run_forever(self):
        asyncio.get_event_loop().run_until_complete(self.run_async())

    #############

    def _callback(self, msg):
        if "channel" in msg:
            channel_callback = self._get_callback(msg["channel"], msg["params"])
            if channel_callback:
                channel_callback(msg)
    
        self.user_callback(msg)