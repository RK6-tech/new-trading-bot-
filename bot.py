import ccxt
import pandas as pd
import time
import os
import requests
from ta.momentum import RSIIndicator
from ta.trend import MACD, EMAIndicator

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

exchange = ccxt.binance({
    'apiKey': API_KEY,
    'secret': API_SECRET,
    'enableRateLimit': True
})

symbol = 'BTC/USDT'
amount = 0.001

entry_price = None

def send(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      data={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

def get_data():
    bars = exchange.fetch_ohlcv(symbol, '1m', limit=100)
    df = pd.DataFrame(bars, columns=['t','o','h','l','c','v'])
    return df

def indicators(df):
    df['rsi'] = RSIIndicator(df['c'], 14).rsi()
    macd = MACD(df['c'])
    df['macd'] = macd.macd()
    df['signal'] = macd.macd_signal()
    df['ema'] = EMAIndicator(df['c'], 50).ema_indicator()
    return df

def signal(df):
    last = df.iloc[-1]
    prev = df.iloc[-2]

    buy = last['rsi'] < 30 and prev['macd'] < prev['signal'] and last['macd'] > last['signal'] and last['c'] > last['ema']
    sell = last['rsi'] > 70 and prev['macd'] > prev['signal'] and last['macd'] < last['signal']

    if buy:
        return "buy"
    if sell:
        return "sell"
    return "hold"

def run():
    global entry_price

    while True:
        try:
            df = indicators(get_data())
            sig = signal(df)
            price = df['c'].iloc[-1]

            print(sig, price)

            if sig == "buy" and entry_price is None:
                order = exchange.create_market_buy_order(symbol, amount)
                entry_price = price
                send(f"BUY @ {price}")

            elif sig == "sell" and entry_price:
                exchange.create_market_sell_order(symbol, amount)
                send(f"SELL @ {price}")
                entry_price = None

            if entry_price:
                if price < entry_price * 0.98:
                    exchange.create_market_sell_order(symbol, amount)
                    send("STOP LOSS HIT")
                    entry_price = None

                elif price > entry_price * 1.04:
                    exchange.create_market_sell_order(symbol, amount)
                    send("TAKE PROFIT HIT")
                    entry_price = None

            time.sleep(60)

        except Exception as e:
            print(e)
            time.sleep(60)

run()
