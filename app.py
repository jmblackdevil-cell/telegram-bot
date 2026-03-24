import os
import telebot
import time
import threading
from datetime import datetime
import pytz
import yfinance as yf

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
print("TOKEN:", TOKEN)

bot = telebot.TeleBot(TOKEN)

# Fix webhook issue
try:
    bot.delete_webhook()
except:
    pass

IST = pytz.timezone("Asia/Kolkata")

# ================= SAFE SEND =================
def safe_send(chat_id, text, parse_mode="Markdown"):
    try:
        bot.send_message(chat_id, text, parse_mode=parse_mode)
    except:
        bot.send_message(chat_id, text)

# ================= BASIC COMMANDS =================

@bot.message_handler(commands=["start"])
def start(message):
    safe_send(message.chat.id,
        "🤖 *Trading Bot Online*\n\n"
        "Commands:\n"
        "/global - Global market report\n"
        "/time - current time\n"
        "/ping - check bot\n"
    )

@bot.message_handler(commands=["ping"])
def ping(message):
    safe_send(message.chat.id, "🏓 Pong! Bot is alive.")

@bot.message_handler(commands=["time"])
def time_cmd(message):
    now = datetime.now(IST).strftime("%d %b %Y %H:%M:%S IST")
    safe_send(message.chat.id, f"🕒 Current time:\n{now}")

# ================= MARKET FUNCTIONS =================

def fetch_price(ticker):
    try:
        data = yf.Ticker(ticker).fast_info
        price = round(data.last_price, 2)
        prev = round(data.previous_close, 2)
        change = round(((price - prev) / prev) * 100, 2)
        arrow = "🟢" if change >= 0 else "🔴"
        return price, f"{arrow} {change:+.2f}%", change
    except:
        return "N/A", "N/A", 0

def get_asian_markets():
    markets = {
        "Nikkei": "^N225",
        "Hang Seng": "^HSI",
        "KOSPI": "^KS11"
    }
    text = ""
    for name, ticker in markets.items():
        price, chg, _ = fetch_price(ticker)
        text += f"{name}: {price} {chg}\n"
    return text

def get_european_markets():
    markets = {
        "DAX": "^GDAXI",
        "FTSE": "^FTSE",
        "CAC": "^FCHI"
    }
    text = ""
    for name, ticker in markets.items():
        price, chg, _ = fetch_price(ticker)
        text += f"{name}: {price} {chg}\n"
    return text

def get_us_markets():
    markets = {
        "Nasdaq": "^IXIC",
        "S&P500": "^GSPC",
        "Dow": "^DJI"
    }
    text = ""
    for name, ticker in markets.items():
        price, chg, _ = fetch_price(ticker)
        text += f"{name}: {price} {chg}\n"
    return text

def get_gift_nifty():
    price, chg, _ = fetch_price("^NSEI")
    return f"{price} {chg}"

def get_commodities():
    crude, cchg, _ = fetch_price("CL=F")
    gold, gchg, _ = fetch_price("GC=F")
    return f"Crude: {crude} {cchg}\nGold: {gold} {gchg}"

def get_sentiment():
    _, _, c1 = fetch_price("^GSPC")
    _, _, c2 = fetch_price("^IXIC")
    avg = (c1 + c2) / 2

    if avg > 0.4:
        return "🟢 Bullish"
    elif avg < -0.4:
        return "🔴 Bearish"
    else:
        return "⚪ Neutral"

def final_verdict():
    sentiment = get_sentiment()
    if "Bullish" in sentiment:
        return "📈 Market likely GAP UP"
    elif "Bearish" in sentiment:
        return "📉 Market likely GAP DOWN"
    else:
        return "➡️ Market likely SIDEWAYS"

# ================= GLOBAL COMMAND =================

@bot.message_handler(commands=["global"])
def global_report(message):
    try:
        safe_send(message.chat.id, "Fetching global market data...")

        time_now = datetime.now(IST).strftime("%d %b %Y %H:%M IST")

        safe_send(message.chat.id,
            f"🌍 *GLOBAL MARKET REPORT*\n"
            f"{time_now}\n\n"
            f"Sentiment: {get_sentiment()}"
        )

        safe_send(message.chat.id,
            f"🌏 *ASIA*\n{get_asian_markets()}"
        )

        safe_send(message.chat.id,
            f"🌍 *EUROPE*\n{get_european_markets()}"
        )

        safe_send(message.chat.id,
            f"🇺🇸 *US*\n{get_us_markets()}"
        )

        safe_send(message.chat.id,
            f"📉 *GIFT NIFTY*\n{get_gift_nifty()}"
        )

        safe_send(message.chat.id,
            f"🛢 *COMMODITIES*\n{get_commodities()}"
        )

        safe_send(message.chat.id,
            f"🧠 *VERDICT*\n{final_verdict()}"
        )

    except Exception as e:
        print("ERROR:", e)
        safe_send(message.chat.id, f"Error: {e}")

# ================= BACKGROUND LOOP =================

def background_task():
    while True:
        try:
            print("Bot running...")
            time.sleep(30)
        except Exception as e:
            print("Error:", e)

# ================= START =================

print("Bot started...")

polling_thread = threading.Thread(target=bot.polling, kwargs={"none_stop": True})
polling_thread.daemon = True
polling_thread.start()

background_task()
