import os
import telebot
import time
import threading
import requests
import yfinance as yf
from datetime import datetime
import pytz

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# Fix webhook issue safely
try:
    bot.delete_webhook()
except:
    pass

IST = pytz.timezone("Asia/Kolkata")

# ================= SAFE SEND =================
def safe_send(chat_id, text):
    try:
        bot.send_message(chat_id, text, parse_mode="Markdown")
    except:
        bot.send_message(chat_id, text)

# ================= GLOBAL MARKETS =================

MARKETS = {
    "Nikkei": ("^N225", (5,30),(11,30)),
    "Hang Seng": ("^HSI",(7,15),(14,0)),
    "DAX": ("^GDAXI",(13,0),(21,30)),
    "FTSE": ("^FTSE",(13,30),(22,0)),
    "NASDAQ": ("^IXIC",(19,0),(1,30)),
    "S&P 500": ("^GSPC",(19,0),(1,30))
}

def now_ist():
    return datetime.now(IST)

def is_open(open_t, close_t):
    now = now_ist()
    mins = now.hour*60 + now.minute
    o = open_t[0]*60 + open_t[1]
    c = close_t[0]*60 + close_t[1]
    if c < o:
        return mins >= o or mins <= c
    return o <= mins <= c

def fetch_price(ticker):
    try:
        data = yf.Ticker(ticker).fast_info
        price = round(data.last_price,2)
        prev = round(data.previous_close,2)
        chg = round(((price-prev)/prev)*100,2)
        arrow = "🟢" if chg>=0 else "🔴"
        return f"{price} {arrow}{chg}%"
    except:
        return "N/A"

def global_markets():
    text = "🌍 *GLOBAL MARKETS*\n\n"
    for name,(ticker,o,c) in MARKETS.items():
        status = "🟡 OPEN" if is_open(o,c) else "⚫ CLOSED"
        price = fetch_price(ticker)
        text += f"*{name}*\n{price} | {status}\n\n"
    return text

# ================= OPTION CHAIN =================

NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "*/*",
}

def fetch_oi():
    try:
        url = "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY"
        s = requests.Session()
        s.get("https://www.nseindia.com", headers=NSE_HEADERS)
        data = s.get(url, headers=NSE_HEADERS).json()
        return data
    except:
        return None

def get_oi_levels(data):
    records = data["records"]["data"]
    expiry = data["records"]["expiryDates"][0]

    max_ce = 0
    max_pe = 0
    res = sup = None

    for d in records:
        if d["expiryDate"] != expiry:
            continue
        strike = d["strikePrice"]

        ce = d.get("CE",{})
        pe = d.get("PE",{})

        if ce.get("openInterest",0) > max_ce:
            max_ce = ce["openInterest"]
            res = strike

        if pe.get("openInterest",0) > max_pe:
            max_pe = pe["openInterest"]
            sup = strike

    return sup,res

# ================= OI CHANGE TRACKER =================

last_support = None
last_resistance = None

def check_oi_change(chat_id):
    global last_support,last_resistance

    data = fetch_oi()
    if not data:
        return

    sup,res = get_oi_levels(data)

    if last_support and sup != last_support:
        safe_send(chat_id, f"🟢 SUPPORT SHIFTED → {last_support} ➜ {sup}")

    if last_resistance and res != last_resistance:
        safe_send(chat_id, f"🔴 RESISTANCE SHIFTED → {last_resistance} ➜ {res}")

    last_support = sup
    last_resistance = res

# ================= COMMANDS =================

@bot.message_handler(commands=["start"])
def start(msg):
    safe_send(msg.chat.id,
        "🤖 *Trading Bot LIVE*\n\n"
        "/global - markets\n"
        "/oi - support resistance\n"
        "/ping - check bot\n"
    )

@bot.message_handler(commands=["ping"])
def ping(msg):
    safe_send(msg.chat.id,"🏓 Bot alive")

@bot.message_handler(commands=["global"])
def global_cmd(msg):
    safe_send(msg.chat.id,"Fetching markets...")
    safe_send(msg.chat.id, global_markets())

@bot.message_handler(commands=["oi"])
def oi_cmd(msg):
    data = fetch_oi()
    if not data:
        safe_send(msg.chat.id,"❌ OI fetch failed")
        return
    sup,res = get_oi_levels(data)
    safe_send(msg.chat.id,
        f"📊 *OI LEVELS*\n\n"
        f"🟢 Support: {sup}\n"
        f"🔴 Resistance: {res}"
    )

# ================= AUTO ALERT LOOP =================

USER_CHAT_ID = None

def auto_loop():
    global USER_CHAT_ID
    while True:
        try:
            if USER_CHAT_ID:
                now = now_ist().strftime("%H:%M")

                if now in ["09:15","09:30","10:30","12:00","13:30","14:30"]:
                    safe_send(USER_CHAT_ID,"⏰ Market Update")
                    safe_send(USER_CHAT_ID, global_markets())

                # Check OI change every 2 mins
                check_oi_change(USER_CHAT_ID)

            time.sleep(120)

        except Exception as e:
            print("Loop error:",e)

# Save chat id automatically
@bot.message_handler(func=lambda m: True)
def save_user(msg):
    global USER_CHAT_ID
    USER_CHAT_ID = msg.chat.id

# ================= START =================

print("Bot running...")

threading.Thread(target=bot.polling, kwargs={"none_stop":True}).start()
threading.Thread(target=auto_loop).start()
