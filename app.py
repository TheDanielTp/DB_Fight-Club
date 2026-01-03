import telebot
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DB_URI = os.environ.get("DB_URI")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

bot = telebot.TeleBot(BOT_TOKEN) # type: ignore

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome to Fight Club Bot! Type /help to see available commands.")

print("Fight Club Bot is running...")
bot.polling(non_stop=True)