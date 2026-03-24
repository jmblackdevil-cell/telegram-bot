import os
import telebot
import yfinance as yf
from datetime import datetime
import pytz

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

IST = pytz.timezone("Asia/Kolkata")

# ================= SEND =================
def send(chat_id, text):
    try:
        bot.send_message(chat_id, text)
    except:
        pass

# ================= MARKETS =================
MARKETS = {
    "Nikkei": "^N225",
    "Hang Seng": "^HSI",
    "KOSPI": "^KS11",
    "DAX": "^GDAXI",
    "FTSE": "^FTSE",
    "CAC": "^FCHI",
    "Nasdaq": "^IXIC",
    "S&P500": "^GSPC",
    "Dow": "^DJI",
    "Crude": "CL=F",
    "Gold": "GC=F",
    "Gift Nifty": "^NSEI"
}

# ================= FETCH =================
def fetch(ticker):
    try:
        df = yf.download(ticker, period="3d", interval="1d", progress=False, threads=False)

        if df is None or df.empty or len(df) < 2:
            return "N/A", "", 0

        df = df.dropna()

        price = round(df["Close"].iloc[-1], 2)
        prev = round(df["Close"].iloc[-2], 2)

        chg = round(((price - prev) / prev) * 100, 2)
        arrow = "🟢" if chg >= 0 else "🔴"

        return price, f"{arrow} {chg:+.2f}%", chg

    except Exception as e:
        print("FETCH ERROR:", e)
        return "N/A", "", 0

# ================= GLOBAL =================
def global_market():
    score = 0

    asia = ["Nikkei","Hang Seng","KOSPI"]
    europe = ["DAX","FTSE","CAC"]
    us = ["Nasdaq","S&P500","Dow"]

    text = "━━━━━━━━━━━━\n"

    # ASIA
    text += "🌏 ASIA\n"
    for m in asia:
        p, chg_str, chg = fetch(MARKETS[m])
        text += f"{m}: {p} {chg_str}\n"
        score += 1 if chg > 0 else -1

    # EUROPE
    text += "\n🌍 EUROPE\n"
    for m in europe:
        p, chg_str, chg = fetch(MARKETS[m])
        text += f"{m}: {p} {chg_str}\n"
        score += 1 if chg > 0 else -1

    # US
    text += "\n🇺🇸 US\n"
    for m in us:
        p, chg_str, chg = fetch(MARKETS[m])
        text += f"{m}: {p} {chg_str}\n"
        score += 1 if chg > 0 else -1

    # GIFT NIFTY
    text += "\n📉 GIFT NIFTY\n"
    p, chg_str, chg = fetch(MARKETS["Gift Nifty"])
    text += f"{p} {chg_str}\n"

    # COMMODITIES
    text += "\n🛢 COMMODITIES\n"
    p, chg_str, _ = fetch(MARKETS["Crude"])
    text += f"Crude: {p} {chg_str}\n"

    p, chg_str, _ = fetch(MARKETS["Gold"])
    text += f"Gold: {p} {chg_str}\n"

    text += "━━━━━━━━━━━━\n"

    # SENTIMENT
    if score > 3:
        sentiment = "🟢 Bullish"
    elif score < -3:
        sentiment = "🔴 Bearish"
    else:
        sentiment = "⚪ Neutral"

    # TIME
    now = datetime.now(IST).strftime("%d %b %Y %H:%M IST")

    # FINAL OUTPUT
    final = f"""
🌍 GLOBAL MARKET REPORT
{now}

Sentiment: {sentiment}

{text}
"""

    return final

# ================= COMMANDS =================
@bot.message_handler(commands=["start"])
def start(msg):
    send(msg.chat.id, "🤖 Global Market Bot Ready\nUse /global")

@bot.message_handler(commands=["global"])
def global_cmd(msg):
    send(msg.chat.id, global_market())

# ================= RUN =================
print("Bot running...")
bot.infinity_polling()
