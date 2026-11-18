import os
import json
import urllib.request
from flask import Flask, request
import telebot
from telebot import types

app = Flask(__name__)

def get_usd_syp():
    url = "https://exchangerate-api.com"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=4) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return round(float(data["rates"]["SYP"]), 2)

@app.route('/', methods=['POST', 'GET'])
def webhook():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        return "BOT_TOKEN missing", 500
        
    bot = telebot.TeleBot(token, threaded=False)

    @bot.message_handler(commands=['start', 'syp'])
    def send_price(message):
        try:
            rate = get_usd_syp()
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 تحديث السعر", callback_data="refresh"))
            text = (
                "💵 **سعر صرف الدولار مقابل الليرة السورية**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🇺🇸 **1 دولار أمريكي** = `{rate:,}` ل.س\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "💡 *أرسل أي مبلغ بالدولار (مثلاً: 50) لتحويله فوراً!*"
            )
            bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطأ: `{str(e)}`", parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data == "refresh")
    def callback_refresh(call):
        try:
            rate = get_usd_syp()
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 تحديث السعر", callback_data="refresh"))
            text = (
                "💵 **سعر صرف الدولار مقابل الليرة السورية (محدّث)**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🇺🇸 **1 دولار أمريكي** = `{rate:,}` ل.س\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "💡 *أرسل أي مبلغ بالدولار لتحويله فوراً!*"
            )
            bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
        except Exception:
            pass
        bot.answer_callback_query(call.id, "✅ تم التحديث!")

    @bot.message_handler(func=lambda message: True)
    def convert_usd(message):
        try:
            amount = float(message.text.strip())
            rate = get_usd_syp()
            total = int(amount * rate)
            bot.reply_to(
                message,
                f"💵 **{amount:,} دولار** = `{total:,}` ليرة سورية",
                parse_mode="Markdown"
            )
        except ValueError:
            bot.reply_to(message, "أرسل `/start` لعرض السعر، أو اكتب رقماً بالدولار (مثل `100`) لتحويله.")
        except Exception as e:
            bot.reply_to(message, f"⚠️ خطأ: `{str(e)}`", parse_mode="Markdown")

    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
        
    return "USD/SYP Bot is Running!", 200
