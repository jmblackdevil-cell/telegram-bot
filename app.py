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

# ================= MARKET CONFIG =================
MARKETS = {
    "Nikkei": ("^N225", "🇯🇵", (5,30),(11,30)),
    "Hang Seng": ("^HSI", "🇭🇰", (7,15),(14,0)),
    "KOSPI": ("^KS11", "🇰🇷", (5,30),(12,30)),
    "DAX": ("^GDAXI", "🇩🇪", (13,0),(21,30)),
    "FTSE": ("^FTSE", "🇬🇧", (13,30),(22,0)),
    "CAC": ("^FCHI", "🇫🇷", (13,30),(22,0)),
    "Nasdaq": ("^IXIC", "🇺🇸", (19,0),(1,30)),
    "S&P500": ("^GSPC", "🇺🇸", (19,0),(1,30)),
    "Dow": ("^DJI", "🇺🇸", (19,0),(1,30)),
}

# ================= HELPERS =================
def now_ist():
    return datetime.now(IST)

def is_open(o, c):
    now = now_ist()
    mins = now.hour*60 + now.minute
    o_m = o[0]*60 + o[1]
    c_m = c[0]*60 + c[1]
    if c_m < o_m:
        return mins >= o_m or mins <= c_m
    return o_m <= mins <= c_m

def fetch_price(ticker):
    try:
        d = yf.Ticker(ticker).fast_info
        price = round(d.last_price,2)
        prev = round(d.previous_close,2)
        chg = round(((price-prev)/prev)*100,2)
        arrow = "🟢" if chg>=0 else "🔴"
        return price, f"{arrow} {chg:+.2f}%", chg
    except:
        return "N/A","",0

# ================= GLOBAL =================
def get_global():
    out = []
    score = 0

    groups = {
        "🌏 ASIA":["Nikkei","Hang Seng","KOSPI"],
        "🌍 EUROPE":["DAX","FTSE","CAC"],
        "🇺🇸 US":["Nasdaq","S&P500","Dow"]
    }

    for g, names in groups.items():
        out.append(g)
        for n in names:
            t,_,o,c = MARKETS[n]
            p,chg_str,chg = fetch_price(t)
            status = "🟡" if is_open(o,c) else "⚫"
            out.append(f"{n}: {p} {chg_str} {status}")
            score += 1 if chg>0 else -1

    sentiment = "🟢 Bullish" if score>3 else ("🔴 Bearish" if score<-3 else "⚪ Neutral")

    return "\n".join(out), sentiment

# ================= TREND ENGINE =================
def get_trend_score():
    try:
        df = yf.download("^NSEI", period="90d", interval="1d", progress=False)

        if df is None or df.empty or len(df) < 20:
            return 0, 0, "Data unavailable"

        # Normalize columns
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

        return score, price, f"MA20:{ma20} MA50:{ma50} RSI:{rsi}"

    except Exception as e:
        print("TREND ERROR:", e)
        return 0, 0, "Error"
📊 NIFTY TREND ANALYSIS

Price: {price}
MA20: {ma20}
MA50: {ma50}

RSI: {rsi}
ATR: {atr}

━━━━━━━━━━━━
TREND SCORE: {score}

{label}

ACTION:
{action}

Confidence: {conf}
"""

    except:
        return "Trend data failed"

# ================= COMMANDS =================

@bot.message_handler(commands=["trend"])
def trend_cmd(msg):
    score, price, info = get_trend_score()

    if price == 0:
        send("⚠️ Trend data not available. Try again.")
        return

    if score >= 3:
        label = "📈 STRONG BULLISH"
    elif score == 2:
        label = "📈 MODERATE BULLISH"
    elif score == 1:
        label = "⚪ WEAK"
    elif score == 0:
        label = "⚪ NO TRADE"
    elif score <= -3:
        label = "📉 STRONG BEARISH"
    else:
        label = "📉 BEARISH"

    send(f"""
📊 NIFTY TREND

Price: {price}

{info}

━━━━━━━━━━━━
Score: {score}
{label}
""")
