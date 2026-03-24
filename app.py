import os
import telebot
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime
import pytz

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

try:
    bot.delete_webhook()
except:
    pass

IST = pytz.timezone("Asia/Kolkata")

# ================= SAFE SEND =================
def send(chat_id, text):
    try:
        bot.send_message(chat_id, text, parse_mode="Markdown")
    except:
        bot.send_message(chat_id, text)

# ================= GLOBAL MARKETS =================
MARKETS = {
    "Nikkei": ("^N225", "🇯🇵"),
    "Hang Seng": ("^HSI", "🇭🇰"),
    "KOSPI": ("^KS11", "🇰🇷"),
    "DAX": ("^GDAXI", "🇩🇪"),
    "FTSE": ("^FTSE", "🇬🇧"),
    "CAC": ("^FCHI", "🇫🇷"),
    "Nasdaq": ("^IXIC", "🇺🇸"),
    "S&P500": ("^GSPC", "🇺🇸"),
    "Dow": ("^DJI", "🇺🇸"),
}

def fetch_price(ticker):
    try:
        df = yf.download(ticker, period="2d", interval="1d", progress=False)
        if df is None or df.empty:
            return "N/A", "", 0

        close = df["Close"]
        price = round(close.iloc[-1], 2)
        prev = round(close.iloc[-2], 2) if len(close) > 1 else price

        chg = round(((price - prev) / prev) * 100, 2)
        arrow = "🟢" if chg >= 0 else "🔴"

        return price, f"{arrow} {chg:+.2f}%", chg
    except:
        return "N/A", "", 0

def get_global():
    out = []
    score = 0

    groups = {
        "🌏 ASIA": ["Nikkei","Hang Seng","KOSPI"],
        "🌍 EUROPE": ["DAX","FTSE","CAC"],
        "🇺🇸 US": ["Nasdaq","S&P500","Dow"]
    }

    for g, names in groups.items():
        out.append(g)
        for n in names:
            t, flag = MARKETS[n]
            p, chg_str, chg = fetch_price(t)
            out.append(f"{flag} {n}: {p} {chg_str}")
            score += 1 if chg > 0 else -1

    sentiment = "🟢 Bullish" if score > 3 else ("🔴 Bearish" if score < -3 else "⚪ Neutral")

    return "\n".join(out), sentiment

# ================= TREND ENGINE =================
def get_trend():
    try:
        df = yf.download("^NSEI", period="3mo", interval="1d", progress=False)

        if df is None or df.empty or len(df) < 20:
            return None

        close = df["Close"]

        price = round(close.iloc[-1], 0)
        ma20 = round(close.rolling(20).mean().iloc[-1], 0)
        ma50 = round(close.rolling(50).mean().iloc[-1], 0)

        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        rsi = round((100 - (100 / (1 + rs))).iloc[-1], 1)

        # ATR
        high = df["High"]
        low = df["Low"]
        tr = (high - low)
        atr = round(tr.rolling(14).mean().iloc[-1], 0)

        # SCORE
        score = 0
        score += 1 if price > ma20 else -1
        score += 1 if ma20 > ma50 else -1

        if rsi > 60:
            score += 1
        elif rsi < 40:
            score -= 1

        # LABEL
        if score >= 3:
            label = "📈 STRONG BULLISH"
            action = "Buy on dips (CE)"
            conf = "HIGH"
        elif score == 2:
            label = "📈 MODERATE BULLISH"
            action = "Buy cautiously"
            conf = "MEDIUM"
        elif score == 1:
            label = "⚪ WEAK"
            action = "Avoid trades"
            conf = "LOW"
        elif score == 0:
            label = "⚪ NO TRADE"
            action = "Wait"
            conf = "LOW"
        elif score <= -3:
            label = "📉 STRONG BEARISH"
            action = "Buy PE"
            conf = "HIGH"
        else:
            label = "📉 BEARISH"
            action = "Sell on rise"
            conf = "MEDIUM"

        return f"""
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

    except Exception as e:
        print("TREND ERROR:", e)
        return None

# ================= COMMANDS =================
@bot.message_handler(commands=["start"])
def start(msg):
    send(msg.chat.id, "🤖 Bot Running\n\n/global\n/trend")

@bot.message_handler(commands=["global"])
def global_cmd(msg):
    data, sentiment = get_global()
    now = datetime.now(IST).strftime("%d %b %Y %H:%M IST")

    send(msg.chat.id, f"""
🌍 GLOBAL MARKET REPORT
{now}

Sentiment: {sentiment}

{data}
""")

@bot.message_handler(commands=["trend"])
def trend_cmd(msg):
    res = get_trend()

    if not res:
        send(msg.chat.id, "⚠️ Trend data failed. Try again later.")
        return

    send(msg.chat.id, res)

# ================= RUN =================
print("Bot running...")
bot.infinity_polling()
