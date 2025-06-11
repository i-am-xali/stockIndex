import requests
import json
import time
from flask import Flask, jsonify
from tradingview_ta import TA_Handler, Interval
from datetime import datetime

app = Flask(__name__)

# Webhook URL
webhook_url = "https://hook.eu2.make.com/ietls2a87fkk5t83k05gnqvviq6mm5ax"

# List of stock symbols
symbols = ['AVN', 'SYS', 'MEBL', 'OGDC', 'LUCK', 'MLCF', 'FCCL', 'HCAR', 'SAZEW', 'KSE100']

# File to store price history (temporary bypass for Vercel)
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
    return {}  # Bypass file operation for now

# Function to save prices (temporary console log)
def save_prices(prices):
    print("Prices would be saved:", prices)  # Log to console instead of file

# Function to check for holidays
def is_holiday(current_prices, previous_prices):
    if not previous_prices:
        return False
    same_price_count = sum(1 for ticker in symbols if isinstance(current_prices.get(ticker), (int, float)) and 
                          isinstance(previous_prices.get(ticker), (int, float)) and 
                          current_prices[ticker] == previous_prices[ticker])
    return same_price_count >= 3

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
            save_prices(log_entry)
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
