import asyncio
import decimal
import requests
import pandas as pd
import numpy as np
import time
from ta.momentum import RSIIndicator
from ta.trend import MACD, SMAIndicator, EMAIndicator
from telegram import Bot

# 🔹 Set up Telegram bot
TELEGRAM_TOKEN = "your bot token"
CHAT_ID = "your id"
bot = Bot(token=TELEGRAM_TOKEN)

# 🔹 Crypto IDX API URL
CRYPTO_IDX_API = "https://tradingpoin.com/chart/api/data?type=json&last=50&token=&pair_code=CRYIDX.B&timeframe=60&load_count=0&source=Binomo&val=Z-CRY/IDX"

# Store the last signal to avoid spam
last_signal = None
price_data = []
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# 🔹 Fetch Last 50 Historical Crypto IDX Prices
def get_historical_crypto_idx_prices():
    try:
        response = requests.get(CRYPTO_IDX_API)
        data = response.json()

        if "data" not in data or not data["data"]:
            print("⚠ No historical data available!")
            return []

        # Extract closing prices from the API response
        prices = [decimal.Decimal(entry[4]) for entry in data["data"] if entry[4] != ""]
        print(f"✅ Loaded {len(prices)} historical prices.")
        return prices

    except Exception as e:
        print(f"⚠ Error fetching historical Crypto IDX prices: {e}")
        return []

# 🔹 Fetch Latest Crypto IDX Price
def get_crypto_idx_price():
    try:
        response = requests.get(CRYPTO_IDX_API.replace("last=50", "last=1"))
        data = response.json()

        if "data" not in data or not data["data"]:
            print("⚠ No live price data available!")
            return None

        latest_data = data["data"]

        # Ensure it's a valid list and contains at least 5 elements
        if isinstance(latest_data, list) and len(latest_data) > 4 and isinstance(latest_data[4], (int, float)):
            price = decimal.Decimal(latest_data[4])
            return price
        return price

    except Exception as e:
        print(f"⚠ Error fetching Crypto IDX price: {e}")
        return None

# 🔹 Calculate Technical Indicators
def calculate_indicators(prices):
    df = pd.DataFrame({"close": prices}, dtype="object")  # Use object type for high precision
    df['RSI'] = RSIIndicator(df['close'].astype(float), window=7).rsi()  # Shorter RSI for quick signals
    df['MACD'] = MACD(df['close'].astype(float), window_slow=12, window_fast=5, window_sign=3).macd()  # Fast MACD
    df['MACD_Signal'] = MACD(df['close'].astype(float), window_slow=12, window_fast=5, window_sign=3).macd_signal()
    df['SMA'] = SMAIndicator(df['close'].astype(float), window=10).sma_indicator()  # Short SMA
    df['EMA'] = EMAIndicator(df['close'].astype(float), window=5).ema_indicator()  # Fast EMA
    return df.dropna()

# 🔹 Generate and Send Trading Signal
def generate_and_send_signal():
    global last_signal
    df = calculate_indicators(price_data)
    
    if df.empty:
        print("⚠ Not enough valid data for indicators yet.")
        return

    latest = df.iloc[-1]
    previous = df.iloc[-2] if len(df) > 1 else None
    signal = "NO SIGNAL"

    # 🔍 **DEBUGGING: Print Technical Indicator Values**
    print(f"📊 Latest Indicators:")
    print(f"   - Price: {latest['close']:.10f}")
    print(f"   - RSI: {latest['RSI']:.2f}")
    print(f"   - MACD: {latest['MACD']:.10f}")
    print(f"   - SMA: {latest['SMA']:.10f}")
    print(f"   - EMA: {latest['EMA']:.10f}")

    # **Updated Trading Conditions**
    if latest['RSI'] < 50 and latest['MACD'] > latest['MACD'] - 0.000000001 and latest['close'] > latest['EMA']:
        signal = "BUY 📈"
    elif latest['RSI'] > 50 and latest['MACD'] < latest['MACD'] + 0.000000001 and latest['close'] < latest['EMA']:
        signal = "SELL 📉"

    # **MACD Crossover Strategy**
    if previous is not None:
        if latest['MACD'] > latest['MACD_Signal'] and previous['MACD'] < previous['MACD_Signal']:
            signal = "BUY 📈 (MACD Cross)"
        elif latest['MACD'] < latest['MACD_Signal'] and previous['MACD'] > previous['MACD_Signal']:
            signal = "SELL 📉 (MACD Cross)"

    # Send signal only if it has changed
    # if signal != "NO SIGNAL" and signal != last_signal:
    loop.run_until_complete(bot.send_message(chat_id=CHAT_ID, text=f"🚀 Crypto IDX Signal: {signal}"))
    print(f"📢 Sent Signal: {signal}")
    last_signal = signal
    

# **🔹 Main Loop: Fetch Data & Send Signals Every Minute**
if __name__ == "__main__":
    # Load historical price data at startup
    price_data = get_historical_crypto_idx_prices()

    while True:
        price = get_crypto_idx_price()
        if price:
            print(f"📊 Crypto IDX Price: {price}")
            price_data.append(price)

            # Keep only the last 50 data points
            if len(price_data) > 50:
                price_data.pop(0)

            # Ensure we have at least 20+ data points before calculating indicators
            if len(price_data) >= 20:
                generate_and_send_signal()

        time.sleep(60)  
