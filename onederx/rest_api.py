import time
import hmac
import json
import hashlib
import requests

from decimal import Decimal

TIMEOUT_SEC = 10

class BadResponseError(Exception):
    def __init__(self, url, payload, reply_text, headers=None):
        self.url = url
        self.payload = payload
        self.headers = headers if headers else {}
        self.reply_text = reply_text
        self.reply_json = self.error_code = self.error_msg = None
        if "error_code" in reply_text:
            self.reply_json = json.loads(reply_text)
            self.error_code = self.reply_json["error_code"]
            self.error_msg = self.reply_json["error_msg"]

    def __str__(self):
        return f"Fail to call {self.url}, payload={self.payload}, headers={self.headers}. Reply: {self.reply_text}"


class OrderNotFoundError(Exception):
    pass


class OnederxREST:
    def __init__(self, base_url, api_key=None, secret=None):
        self.base_url = base_url
        self.api_key = api_key
        self.secret = secret

        self.session = requests.Session()

    def _get_json(self, url, data={}):
        result = self.session.get(
            self.base_url + url,
            json=data,
            timeout=TIMEOUT_SEC)
        if result.status_code != 200:
            raise BadResponseError(url, data, result.text)
        return result.json()

    # Public endpoints
    def get_status(self):
        return self._get_json("/v1/status")

    def get_symbols_details(self):
        return self._get_json("/v1/symbol_details")

    def get_ticker(self, symbol):
        return self._get_json("/v1/ticker", data={"symbol": symbol})

    def get_l2_snapshot(self, symbol):
        return self._get_json("/v1/l2", data={"symbol": symbol})

    def get_l3_snapshot(self, symbol):
        return self._get_json("/v1/l3", data={"symbol": symbol})

    def get_historic_candles(
            self,
            symbol,
            resolution,
            from_nanosec,
            to_nanosec):
        payload = {
            "symbol": symbol,
            "resolution": resolution,
            "from": from_nanosec,
            "to": to_nanosec
        }
        return self._get_json("/v1/candles", data=payload)

    # Private methods

    def _signature_payload(self, url, payload_string):
        string_to_sign = url + payload_string

        signature = hmac.new(
            self.secret.encode(),
            msg=string_to_sign.encode(),
            digestmod=hashlib.sha512).hexdigest()
        return signature

    def _unix_nanosec(self):
        return int(time.time() * 1e9)

    def _calc_header(self, url, payload_string):
        signature = self._signature_payload(url, payload_string)
        return {"APIKEY": self.api_key, "SIGNATURE": signature}

    def _private_call(self, symbol, url, payload):
        if self.secret is None or self.api_key is None:
            raise Exception(
                "You should provide secret & api_key before calling private methods")

        payload = dict(payload)
        payload.update({"timestamp": self._unix_nanosec(), "symbol": symbol})
        payload_string = json.dumps(payload)

        headers = self._calc_header(url, payload_string)
        result = self.session.post(
            self.base_url + url,
            data=payload_string,
            headers=headers,
            timeout=TIMEOUT_SEC)

        if result.status_code != 200:
            raise BadResponseError(url, payload, result.text, headers=headers)

        if result.text == "":
            return {}
        return result.json()

    def _prive_call_noargs(self, url):
        return self._private_call(None, url, {})

    def cancel_all_orders(self, symbol):
        return self._private_call(symbol, "/v1/order/cancel/all", {})

    def cancel_all_stop_orders(self, symbol):
        return self._private_call(symbol, "/v1/order/cancel_all_stop", {})

    def new_order(
            self,
            symbol,
            my_id,
            side,
            price,
            volume,
            order_type,
            time_in_force,
            is_post_only,
            is_stop):
        def to_str(x): return str(Decimal(x))
        payload = {
            "volume": to_str(volume),
            "price": to_str(price),
            "side": side,
            "type": order_type,
            "time_in_force": time_in_force,
            "post_only": is_post_only,
            "stop": is_stop,
            "cl_ord_id": str(my_id)
        }
        return self._private_call(symbol, "/v1/order/new", payload)

    def cancel_order(self, symbol, order_id):
        try:
            self._private_call(symbol, "/v1/order/cancel",
                               {"order_id": order_id})
        except BadResponseError as exception:
            if exception.error_code == 42:
                raise OrderNotFoundError(str(exception))
            else:
                raise exception

    def get_orders(self, symbol):
        return self._private_call(symbol, "/v1/l3_private", {})

    def get_stop_orders(self, symbol):
        return self._private_call(symbol, "/v1/stop_orders", {})

    def generate_new_wallet(self, currency):
        return self._private_call(
            None, "/v1/wallets/generate", {"curr": currency})

    def generate_withdraw(self, currency, amount, address):
        return self._private_call(None,
                                  "/v1/wallets/withdraw",
                                  {"curr": currency,
                                   "amount": amount,
                                   "address": address})

    def get_wallets_list(self):
        return self._private_call(None, "/v1/wallets/list", {})

    def get_withdrawal_history(self):
        return self._private_call(None, "/v1/wallets/withdrawal_history", {})

    def get_deposit_history(self):
        return self._private_call(None, "/v1/wallets/deposit_history", {})

    def get_balances(self):
        return self._private_call(None, "/v1/balances", {})

    def get_positions(self):
        return self._private_call(None, "/v1/positions", {})

    def get_my_trades(self, symbol):
        return self._private_call(symbol, "/v1/trades_private", {})