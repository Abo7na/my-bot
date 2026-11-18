import os
from flask import Flask, request
import telebot

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def webhook():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        return "Error: BOT_TOKEN not found!", 500
        
    bot = telebot.TeleBot(token, threaded=False)

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        bot.reply_to(message, "أهلاً بك! البوت يعمل بنجاح على مدار 24 ساعة مجاناً 🚀")

    @bot.message_handler(func=lambda message: True)
    def echo_all(message):
        bot.reply_to(message, f"وصلت رسالتك: {message.text}")

    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
        
    return "Telegram Bot is Alive and Token is Set!", 200
