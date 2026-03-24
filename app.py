import os
import telebot
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import time
import threading

# CONFIG
TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = telebot.TeleBot(TOKEN)
bot.delete_webhook()

IST = pytz.timezone("Asia/Kolkata")

def now():
    return datetime.now(IST)

def send(msg):
    try:
        bot.send_message(CHAT_ID, msg, parse_mode="Markdown")
    except:
        bot.send_message(CHAT_ID, msg)

# ================= TREND =================
def get_trend_score():
    df = yf.download("^NSEI", period="60d", interval="1d", progress=False)
    close = df["Close"]

    ma20 = close.rolling(20).mean().iloc[-1]
    ma50 = close.rolling(50).mean().iloc[-1]
    price = close.iloc[-1]

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = (100 - (100 / (1 + rs))).iloc[-1]

    score = 0
    score += 1 if price > ma20 else -1
    score += 1 if ma20 > ma50 else -1
    if rsi > 60: score += 1
    elif rsi < 40: score -= 1

    return int(score), round(price,0)

# ================= FVG DETECTION =================
def detect_fvg(df):
    fvg = []

    for i in range(2, len(df)):
        c1 = df.iloc[i-2]
        c2 = df.iloc[i-1]
        c3 = df.iloc[i]

        # Bullish FVG
        if c1["high"] < c3["low"]:
            fvg.append(("bullish", c1["high"], c3["low"]))

        # Bearish FVG
        if c1["low"] > c3["high"]:
            fvg.append(("bearish", c3["high"], c1["low"]))

    return fvg[-5:] if fvg else []

# ================= IFVG =================
def detect_ifvg(df):
    return detect_fvg(df)

# ================= ICT SIGNAL =================
def ict_signal():
    try:
        score, price = get_trend_score()

        htf = yf.download("^NSEI", period="1d", interval="5m", progress=False)
        ltf = yf.download("^NSEI", period="1d", interval="1m", progress=False)

        htf.columns = htf.columns.str.lower()
        ltf.columns = ltf.columns.str.lower()

        fvg_zones = detect_fvg(htf)
        ifvg_zones = detect_ifvg(ltf)

        for fvg_type, low, high in fvg_zones[::-1]:

            # price inside FVG
            if low <= price <= high:

                for ifvg_type, ilow, ihigh in ifvg_zones[::-1]:

                    # BEARISH LOGIC
                    if fvg_type == "bearish" and ifvg_type == "bullish" and score <= -2:
                        return f"""
🚨 ICT SIGNAL

Type: BEARISH IFVG ENTRY
Price: {price}
Zone: {low:.0f} – {high:.0f}

Trend Score: {score}

Entry: Breakdown candle
SL: Above zone
TP: Previous low

Confidence: HIGH
"""

                    # BULLISH LOGIC
                    if fvg_type == "bullish" and ifvg_type == "bearish" and score >= 2:
                        return f"""
🚨 ICT SIGNAL

Type: BULLISH IFVG ENTRY
Price: {price}
Zone: {low:.0f} – {high:.0f}

Trend Score: {score}

Entry: Breakout candle
SL: Below zone
TP: Previous high

Confidence: HIGH
"""

        return None

    except Exception as e:
        return f"Error: {e}"

# ================= COMMANDS =================
@bot.message_handler(commands=["start"])
def start(msg):
    send("🔥 PRO ICT BOT ACTIVE\n\n/global\n/trend\n/signal")

@bot.message_handler(commands=["signal"])
def signal(msg):
    send("Scanning ICT setup...")
    s = ict_signal()
    send(s if s else "No high probability setup")

# ================= AUTO ALERT =================
def auto_loop():
    while True:
        try:
            sig = ict_signal()
            if sig:
                send(sig)
                time.sleep(300)  # avoid spam
        except Exception as e:
            print(e)
        time.sleep(60)

# ================= START =================
print("BOT RUNNING")

threading.Thread(target=bot.polling, kwargs={"none_stop":True}).start()
threading.Thread(target=auto_loop).start()

while True:
    time.sleep(10)
