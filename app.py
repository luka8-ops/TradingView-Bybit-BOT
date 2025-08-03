import os
from flask import Flask, request, jsonify
from binance.client import Client
import logging

from binance_sdk_derivatives_trading_usds_futures.derivatives_trading_usds_futures import (
    DerivativesTradingUsdsFutures,
    ConfigurationRestAPI,
    DERIVATIVES_TRADING_USDS_FUTURES_REST_API_PROD_URL,
)
from binance_sdk_derivatives_trading_usds_futures.rest_api.models import (
    NewOrderSideEnum,
)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create configuration for the REST API
configuration_rest_api = ConfigurationRestAPI(
    api_key=os.getenv("BINANCE_API_KEY", ""),
    api_secret=os.getenv("BINANCE_API_SECRET", ""),
    base_path=os.getenv(
        "BASE_PATH", DERIVATIVES_TRADING_USDS_FUTURES_REST_API_PROD_URL
    ),
)

# Initialize DerivativesTradingUsdsFutures client
binance_client = DerivativesTradingUsdsFutures(config_rest_api=configuration_rest_api)

app = Flask(__name__)

@app.route('/')
def home():
    return "Webhook bot is running!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Received webhook:", data)

    if data.get("secret") != "my_secret_key":
        return jsonify({"error": "unauthorized"}), 403

    symbol = data.get("symbol", "BTCUSDT")
    action = data.get("action")
    quantity = float(data.get("quantity", 0.01))
    tp = float(data.get("tp"))
    sl = float(data.get("sl"))
    leverage = int(data.get("leverage", 10))

    change_initial_leverage(leverage)

    if action in ["buy", "sell"]:
        result = place_order(symbol, action.upper(), quantity, tp, sl)
        return jsonify({"status": "order sent", "result": result}), 200
    else:
        return jsonify({"error": "invalid action"}), 400

# Place Order Function
def place_order(symbol, side, quantity, tp_price, sl_price):
    try:
        # 1. Place entry (market order)
        response = binance_client.rest_api.new_order(
            symbol=symbol,
            side=NewOrderSideEnum[side].value,
            type="MARKET",
            quantity=quantity,
        )
        logging.info(f"Market order placed: {response.data()}")

        # 2. Take Profit order
        tp_order = binance_client.rest_api.new_order(
            symbol=symbol,
            side="SELL" if side == "BUY" else "BUY",
            type="TAKE_PROFIT_MARKET",
            stop_price=tp_price,
            close_position=True,
        )
        logging.info(f"TP order placed: {tp_order.data()}")

        # 3. Stop Loss order
        sl_order = binance_client.rest_api.new_order(
            symbol=symbol,
            side="SELL" if side == "BUY" else "BUY",
            type="STOP_MARKET",
            stop_price=sl_price,
            close_position=True,
        )
        logging.info(f"SL order placed: {sl_order.data()}")

        return {
            "entry": response.data(),
            "tp": tp_order.data(),
            "sl": sl_order.data(),
        }

    except Exception as e:
        logging.error(f"Error placing order or TP/SL: {e}")
        return {"error": str(e)}


# Set custom Leverage Function
def change_initial_leverage(currency_pair, custom_leverage):
    try:
        response = binance_client.rest_api.change_initial_leverage(
            symbol=currency_pair,
            leverage=custom_leverage,
        )

        rate_limits = response.rate_limits
        logging.info(f"change_initial_leverage() rate limits: {rate_limits}")

        data = response.data()
        logging.info(f"change_initial_leverage() response: {data}")
    except Exception as e:
        logging.error(f"change_initial_leverage() error: {e}")