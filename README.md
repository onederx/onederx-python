# onederx-python
[![PyPI version](https://img.shields.io/badge/pypi-v.0.0.5-green.svg)](https://pypi.org/project/onederx/)
[![Python support](https://img.shields.io/badge/python-3.6%20%7C%203.7%2B-green.svg)](https://www.python.org/)
[![MIT license](https://img.shields.io/badge/License-MIT-blue.svg)](https://lbesson.mit-license.org/)

## What is it?
This  library provides Python interface for [Onederx REST and Websockets API](https://docs.onederx.com/). It's compatible with Python versions 3.6+. 
Python 2 is not supported due to lack of `asyncio` support.

## What is Onederx?
[Onederx](https://onederx.com) is crypto derivatives trading platform launched in 2018. The main trading instrument is `BTCUSD_P` which is Perpetual contract with a leverage up to **20x**.

**UPDATE:** We added Meme-trading 🔥! `MEMES-BTC` is a Perpetual contract based on Onederx Meme-Index. More info: [https://memes.onederx.com](https://memes.onederx.com).


## Installing
You can install or upgrade onederx-python with:

`$ pip install onederx --upgrade`

## REST API example
```python
from onederx import OnederxREST
rest_api = OnederxREST(base_url="https://api.onederx.com")
symbol = "BTCUSD_P"

# Get ticker 24h summary 
rest_api.get_ticker(symbol)

# Get l2 orderbook
rest_api.get_l2_snapshot(symbol)

# Get l3 orderbook, order-by-order
rest_api.get_l3_snapshot(symbol)

# Get all available symbols & details.
rest_api.get_symbols_details()
```
## Sending and canceling orders via REST
```python
from onederx import OnederxREST
# MY_API_KEY, MY_SECRET = ..., ... 
rest_api = OnederxREST(base_url="https://api.onederx.com", api_key=MY_API_KEY, secret=MY_SECRET)

# Sending buy order
rest_api.new_order(
            symbol="BTCUSD_P",
            my_id="rnd_string",  # put random string here
            side="buy",
            price=1000,
            volume=1,
            order_type="limit",
            time_in_force="gtc",
            is_post_only=False,
            is_stop=False)

# Get all my orders
rest_api.get_orders("BTCUSD_P")

# Cancell all orders
rest_api.cancel_all_orders("BTCUSD_P")

# Get my balances
rest_api.get_balances()
```

## Websockets API example 
```python
from onederx import OnederxWebsockets

# Callback for all messages: errors & system messages
def main_callback(data):
    print("Callback:", data)

# Callback for trades messages
def trades_callback(data):
    print("Trades msg:", data)

ws = OnederxWebsockets(user_callback=main_callback, base_url="wss://api.onederx.com")

# Subscribe for trades channel
ws.subscribe_trades(callback=trades_callback, symbol="BTCUSD_P")

# Run asyncio cycle forever
ws.run_forever()
```

## Sending and canceling orders via Websockets
```python
from onederx import OnederxWebsockets

# MY_API_KEY, MY_SECRET = ..., ... 
ws = OnederxWebsockets(user_callback=print, base_url="wss://api.onederx.com", api_key=MY_API_KEY, secret=MY_SECRET)

# Authentication 
ws.auth()

# Subscribe to action replies
ws.subscribe_action_replies(callback=print, symbol="BTCUSD_P")

# Sending buy order
ws.new_order(
    symbol="BTCUSD_P",
    my_id="rnd_string",  # put random string here
    side="buy",
    price=1000,
    volume=1,
    order_type="limit",
    time_in_force="gtc",
    is_post_only=False,
    is_stop=False)

# Canceling all orders
ws.cancel_all_orders(symbol="BTCUSD_P")

# Run asyncio cycle forever
ws.run_forever()
```

## Example of using `asyncio` event loop

```python
asyncio.get_event_loop().run_until_complete(ws.run_async())
```


## More info
* API Documentation link: [https://docs.onederx.com/](https://docs.onederx.com/)

* You can ask any question in our friendly Telegram community: [@onederx](https://t.me/onederx).