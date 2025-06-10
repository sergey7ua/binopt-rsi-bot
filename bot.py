import time
import os
import requests
import pandas as pd
from binance.client import Client
from ta.momentum import RSIIndicator
from dotenv import load_dotenv

load_dotenv()

# --- Змінні середовища ---
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SYMBOL = 'BTCUSDT'
INTERVAL = Client.KLINE_INTERVAL_1MINUTE
RSI_PERIOD = 14

# --- Binance клієнт ---
client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)

# --- Отримання свічок ---
def get_klines(symbol, interval, limit=100):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)
    return df

# --- Патерни ---
def is_bullish_engulfing(o1, c1, o2, c2):
    return (c1 < o1) and (c2 > o2) and (o2 < c1) and (c2 > o1)

def is_bearish_engulfing(o1, c1, o2, c2):
    return (c1 > o1) and (c2 < o2) and (o2 > c1) and (c2 < o1)

def is_hammer(o, c, h, l):
    body = abs(c - o)
    lower = min(o, c) - l
    upper = h - max(o, c)
    return lower > 2 * body and upper < body

def is_shooting_star(o, c, h, l):
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    return upper > 2 * body and lower < body

# --- Аналіз ---
def analyze(df):
    rsi = RSIIndicator(close=df['close'], window=RSI_PERIOD).rsi()
    last_rsi = rsi.iloc[-1]

    # 3 останні свічки
    o1, c1 = df['open'].iloc[-3], df['close'].iloc[-3]
    o2, c2 = df['open'].iloc[-2], df['close'].iloc[-2]
    o3, c3 = df['open'].iloc[-1], df['close'].iloc[-1]
    h3, l3 = df['high'].iloc[-1], df['low'].iloc[-1]

    if last_rsi < 30:
        if is_bullish_engulfing(o1, c1, o2, c2) or is_hammer(o3, c3, h3, l3):
            return "BUY"
    elif last_rsi > 70:
        if is_bearish_engulfing(o1, c1, o2, c2) or is_shooting_star(o3, c3, h3, l3):
            return "SELL"
    return None

# --- Telegram ---
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print(f"Telegram error: {e}")

# --- Основний цикл ---
print("Сигнальний бот запущено.")
while True:
    try:
        df = get_klines(SYMBOL, INTERVAL)
        signal = analyze(df)
        if signal:
            price = df['close'].iloc[-1]
            msg = f"{signal} сигнал по {SYMBOL} @ {price:.2f}"
            send_telegram(msg)
            print(msg)
        else:
            print("Сигналів немає.")
    except Exception as e:
        print(f"Помилка: {e}")
    time.sleep(60)
