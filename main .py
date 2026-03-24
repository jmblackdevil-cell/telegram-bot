import os
import telebot
import time
import threading
from datetime import datetime
import pytz

# ================= CONFIG =================
TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(TOKEN)

# ✅ IMPORTANT: remove webhook (fixes your issue)
bot.delete_webhook()

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
        "✅ Bot is working correctly\n\n"
        "Try:\n"
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

# ================= AUTO LOOP =================

def background_task():
    while True:
        try:
            print("Bot running...")
            time.sleep(30)
        except Exception as e:
            print("Error:", e)

# ================= START BOT =================

print("Bot started...")

# Start polling in thread
polling_thread = threading.Thread(target=bot.polling, kwargs={"none_stop": True})
polling_thread.daemon = True
polling_thread.start()

# Background loop
background_task()
