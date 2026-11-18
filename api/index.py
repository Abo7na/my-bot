import os
import json
import urllib.request
from flask import Flask, request
import telebot
from telebot import types

app = Flask(__name__)

def get_usd_syp():
    urls = [
        "https://jsdelivr.net",
        "https://er-api.com"
    ]
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # المحاولة 1: شبكة jsdelivr السريعة جداً (تعمل دائماً على Vercel)
    try:
        req = urllib.request.Request(urls[0], headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            syp = data["usd"]["syp"]
            return round(float(syp), 2)
    except Exception as e1:
        err1 = str(e1)

    # المحاولة 2: المصدر الاحتياطي
    try:
        req = urllib.request.Request(urls[1], headers=headers)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            syp = data["rates"]["SYP"]
            return round(float(syp), 2)
    except Exception as e2:
        return f"ERR: {err1} | {str(e2)}"

@app.route('/', methods=['POST', 'GET'])
def webhook():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        return "BOT_TOKEN missing", 500
        
    bot = telebot.TeleBot(token, threaded=False)

    @bot.message_handler(commands=['start', 'syp'])
    def send_price(message):
        rate = get_usd_syp()
        if isinstance(rate, str):
            bot.reply_to(message, f"⚠️ تفاصيل الخطأ:\n`{rate}`", parse_mode="Markdown")
            return
            
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

    @bot.callback_query_handler(func=lambda call: call.data == "refresh")
    def callback_refresh(call):
        rate = get_usd_syp()
        if not isinstance(rate, str):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 تحديث السعر", callback_data="refresh"))
            text = (
                "💵 **سعر صرف الدولار مقابل الليرة السورية (محدّث)**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🇺🇸 **1 دولار أمريكي** = `{rate:,}` ل.س\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "💡 *أرسل أي مبلغ بالدولار لتحويله فوراً!*"
            )
            try:
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            except Exception:
                pass
        bot.answer_callback_query(call.id, "✅ تم التحديث!")

    @bot.message_handler(func=lambda message: True)
    def convert_usd(message):
        try:
            amount = float(message.text.strip())
            rate = get_usd_syp()
            if isinstance(rate, str):
                bot.reply_to(message, "⚠️ تعذر جلب السعر حالياً.")
                return
            total = int(amount * rate)
            bot.reply_to(
                message,
                f"💵 **{amount:,} دولار** = `{total:,}` ليرة سورية",
                parse_mode="Markdown"
            )
        except ValueError:
            bot.reply_to(message, "أرسل `/start` لعرض السعر، أو اكتب رقماً بالدولار (مثل `100`) لتحويله.")

    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
        
    return "USD/SYP Bot is Running!", 200
