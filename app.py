import os
import telebot
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz
import time
import threading

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

bot.delete_webhook()

IST = pytz.timezone("Asia/Kolkata")

# ================= SAFE SEND =================
def safe_send(chat_id, text):
    try:
        bot.send_message(chat_id, text, parse_mode="Markdown")
    except:
        bot.send_message(chat_id, text)

# ================= HELPERS =================
def now_ist():
    return datetime.now(IST)

# ================= TREND ENGINE =================
def get_trend_score():
    try:
        df = yf.download("^NSEI", period="90d", interval="1d", progress=False)

        if df is None or df.empty or len(df) < 20:
            return 0, 0, "Data unavailable"

        df.columns = [c.lower() for c in df.columns]
        close = df["close"]

        price = round(float(close.iloc[-1]), 0)

        ma20 = round(float(close.rolling(20).mean().iloc[-1]), 0)
        ma50 = round(float(close.rolling(50).mean().iloc[-1]), 0) if len(close) >= 50 else ma20

        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = round(float(100 - (100 / (1 + rs)).iloc[-1]), 1)

        # SCORE
        score = 0
        score += 1 if price > ma20 else -1
        score += 1 if ma20 > ma50 else -1

        if rsi > 60:
            score += 1
        elif rsi < 40:
            score -= 1

        info = f"MA20: {ma20}\nMA50: {ma50}\nRSI: {rsi}"

        return score, price, info

    except Exception as e:
        print("TREND ERROR:", e)
        return 0, 0, "Error"

# ================= COMMAND =================
@bot.message_handler(commands=["trend"])
def trend_cmd(msg):
    score, price, info = get_trend_score()

    if price == 0:
        safe_send(msg.chat.id, "⚠️ Trend data not available. Try again.")
        return

    if score >= 3:
        label = "📈 STRONG BULLISH"
        action = "Buy CE on dips"
        conf = "HIGH"
    elif score == 2:
        label = "📈 MODERATE BULLISH"
        action = "Buy CE carefully"
        conf = "MEDIUM"
    elif score == 1:
        label = "⚪ WEAK"
        action = "Avoid trades"
        conf = "LOW"
    elif score == 0:
        label = "⚪ NO TRADE"
        action = "Stay out"
        conf = "LOW"
    elif score <= -3:
        label = "📉 STRONG BEARISH"
        action = "Buy PE on rise"
        conf = "HIGH"
    else:
        label = "📉 BEARISH"
        action = "Sell rallies"
        conf = "MEDIUM"

    text = f"""
📊 NIFTY TREND ANALYSIS

Price: {price}

{info}

━━━━━━━━━━━━
TREND SCORE: {score}

{label}

ACTION:
{action}

Confidence: {conf}
"""

    safe_send(msg.chat.id, text)

# ================= START =================
print("Bot running...")

threading.Thread(target=bot.polling, kwargs={"none_stop": True}).start()

while True:
    time.sleep(10)
