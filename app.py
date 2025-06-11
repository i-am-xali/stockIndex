import requests
import json
from flask import Flask, jsonify
from tradingview_ta import TA_Handler, Interval
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# Webhook URL
webhook_url = "https://hook.eu2.make.com/ietls2a87fkk5t83k05gnqvviq6mm5ax"

# List of stock symbols
symbols = ['AVN', 'SYS', 'MEBL', 'OGDC', 'LUCK', 'MLCF', 'FCCL', 'HCAR', 'SAZEW', 'KSE100']

# File to store price history (Vercel is stateless, so this is a temporary file)
PRICE_LOG_FILE = "/tmp/price_log.json"

# Function to fetch current prices
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
            results[ticker] = analysis.indicators['close']
        except Exception as e:
            results[ticker] = f"Error: {str(e)}"
    return results

# Function to load previous prices
def load_previous_prices():
    if os.path.exists(PRICE_LOG_FILE):
        with open(PRICE_LOG_FILE, 'r') as f:
            return json.load(f)
    return {}

# Function to save prices
def save_prices(prices):
    with open(PRICE_LOG_FILE, 'w') as f:
        json.dump(prices, f)

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
    # Get current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    
    # Fetch current prices
    current_prices = fetch_prices()
    
    # Load previous prices
    previous_prices = load_previous_prices()
    
    # Check for holiday
    holiday = is_holiday(current_prices, previous_prices)
    
    # Log prices (unless it's a holiday)
    if not holiday:
        log_entry = {
            "date": current_date,
            "prices": current_prices
        }
        # Append to log (simulating persistent storage)
        log_data = []
        if os.path.exists(PRICE_LOG_FILE):
            with open(PRICE_LOG_FILE, 'r') as f:
                log_data = json.load(f)
            if not isinstance(log_data, list):
                log_data = [log_data]
        log_data.append(log_entry)
        with open(PRICE_LOG_FILE, 'w') as f:
            json.dump(log_data, f)
        
        # Send prices to webhook
        response = requests.post(webhook_url, json=current_prices)
        result = {
            "status_code": response.status_code,
            "response": response.text,
            "holiday": holiday,
            "prices": current_prices
        }
    else:
        result = {
            "message": "Market closed (holiday detected)",
            "holiday": holiday,
            "prices": current_prices
        }
    
    return jsonify(result)

# Root endpoint for testing
@app.route('/')
def home():
    return jsonify({"message": "Flask app running. Use /fetch-prices to fetch stock prices."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)