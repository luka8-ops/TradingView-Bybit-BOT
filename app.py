# app.py
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return "Webhook bot is running!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    print("Received webhook:", data)

    # Example validation
    if data.get("secret") != "my_secret_key":
        return jsonify({"error": "unauthorized"}), 403

    # Extract basic fields
    action = data.get("action")
    symbol = data.get("symbol")

    print(f"Received {action} for {symbol}")
    # TODO: Add real trading logic here (e.g., call exchange API)

    return jsonify({"status": "order received"}), 200
