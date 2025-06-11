import requests
import json
import time
import os
from flask import Flask, jsonify
from tradingview_ta import TA_Handler, Interval
from datetime import datetime

app = Flask(__name__)

# Webhook URL
webhook_url = "https://hook.eu2.make.com/ietls2a87fkk5t83k05gnqvviq6mm5ax"

# List of stock symbols
symbols = ['AVN', 'SYS', 'MEBL', 'OGDC', 'LUCK', 'MLCF', 'FCCL', 'HCAR', 'SAZEW', 'KSE100']

# File to store price history (temporary for Vercel)
PRICE_LOG_FILE = "/tmp/price_log.json"

# Function to fetch current prices with delay
def fetch_prices():
    results = {}
    for ticker in symbols:
        try:
            analysis = TA_Handler(
                symbol=ticker,
                screener='pakistan',
                exchange='PSX',
                interval=Interval.INTERVAL_1_DAY
            ).get_analysis()
            results[ticker] = analysis.indicators.get('close', 'No data')
        except Exception as e:
            results[ticker] = f"Error: {str(e)}"
        time.sleep(1)  # Add 1-second delay between requests
    return results

# Function to load previous prices
def load_previous_prices():
    if os.path.exists(PRICE_LOG_FILE):
        try:
            with open(PRICE_LOG_FILE, 'r') as f:
                data = json.load(f)
                return data.get('prices', {}) if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}

# Function to save prices to file
def save_prices(prices):
    log_entry = {"prices": prices}  # Store only prices for simplicity
    try:
        with open(PRICE_LOG_FILE, 'w') as f:
            json.dump(log_entry, f)
        print("Prices saved to file:", prices)
    except Exception as e:
        print(f"Failed to save prices: {str(e)}")

# Function to check for holidays based on KSE100
def is_holiday(current_prices, previous_prices):
    current_kse100 = current_prices.get('KSE100')
    previous_kse100 = previous_prices.get('KSE100') if previous_prices else None
    if (isinstance(current_kse100, (int, float)) and 
        isinstance(previous_kse100, (int, float)) and 
        current_kse100 == previous_kse100):
        return True
    return False

# Main endpoint to fetch prices and process
@app.route('/fetch-prices', methods=['GET'])
def fetch_prices_endpoint():
    try:
        current_date = datetime.now().strftime("%Y-%m-%d")
        current_prices = fetch_prices()
        previous_prices = load_previous_prices()
        holiday = is_holiday(current_prices, previous_prices)
        
        if not holiday:
            log_entry = {"date": current_date, "prices": current_prices}
            save_prices(current_prices)  # Save current prices for next comparison
            # Skip webhook if all prices are errors
            all_errors = all(isinstance(v, str) and v.startswith("Error:") for v in current_prices.values())
            if not all_errors:
                try:
                    response = requests.post(webhook_url, json=current_prices, timeout=10)
                    result = {
                        "status_code": response.status_code,
                        "response": response.text,
                        "holiday": holiday,
                        "prices": current_prices
                    }
                except requests.RequestException as e:
                    result = {"error": str(e), "holiday": holiday, "prices": current_prices}
            else:
                result = {"message": "All prices errored, webhook skipped", "holiday": holiday, "prices": current_prices}
        else:
            result = {"message": "Market closed (holiday detected)", "holiday": holiday, "prices": current_prices}
    except Exception as e:
        return jsonify({"error": str(e), "message": "Function failed, check logs"}), 500
    return jsonify(result)

# Root endpoint for testing
@app.route('/')
def home():
    return jsonify({"message": "Flask app running. Use /fetch-prices to fetch stock prices."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
