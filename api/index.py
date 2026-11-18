import os
import requests
from flask import Flask, request
import telebot
from telebot import types

app = Flask(__name__)

def get_rates():
    try:
        # تجميع الرابط برمجياً لمنع المتصفح من قصه أثناء النسخ
        host = "api." + "frankfurter" + ".app"
        url = "https://" + host + "/latest?from=USD"
        
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            rates = r.json().get("rates", {})
            return {
                "EUR": rates.get("EUR", "-"),
                "TRY": rates.get("TRY", "-"),
                "GBP": rates.get("GBP", "-"),
                "CAD": rates.get("CAD", "-"),
                "AUD": rates.get("AUD", "-")
            }
        return f"Status: {r.status_code}"
    except Exception as e:
        return f"Err: {str(e)}"

@app.route('/', methods=['POST', 'GET'])
def webhook():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        return "BOT_TOKEN missing", 500
        
    bot = telebot.TeleBot(token, threaded=False)

    @bot.message_handler(commands=['start', 'prices'])
    def send_price(message):
        res = get_rates()
        if isinstance(res, str):
            bot.reply_to(message, f"⚠️ `{res}`", parse_mode="Markdown")
            return
            
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 تحديث الأسعار", callback_data="refresh"))
        
        text = (
            "💱 **أسعار صرف الدولار اليوم**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🇪🇺 **اليورو (EUR):** `{res['EUR']}`\n"
            f"🇹🇷 **الليرة التركية (TRY):** `{res['TRY']}`\n"
            f"🇬🇧 **الجنيه الإسترليني (GBP):** `{res['GBP']}`\n"
            f"🇨🇦 **الدولار الكندي (CAD):** `{res['CAD']}`\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💡 *أرسل أي مبلغ بالدولار لتحويله فوراً!*"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "refresh")
    def callback_refresh(call):
        res = get_rates()
        if not isinstance(res, str):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 تحديث الأسعار", callback_data="refresh"))
            text = (
                "💱 **أسعار صرف الدولار اليوم (محدّثة)**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🇪🇺 **اليورو (EUR):** `{res['EUR']}`\n"
                f"🇹🇷 **الليرة التركية (TRY):** `{res['TRY']}`\n"
                f"🇬🇧 **الجنيه الإسترليني (GBP):** `{res['GBP']}`\n"
                f"🇨🇦 **الدولار الكندي (CAD):** `{res['CAD']}`\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "💡 *أرسل أي مبلغ بالدولار لتحويله!*"
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
            res = get_rates()
            if isinstance(res, str):
                bot.reply_to(message, "⚠️ تعذر جلب السعر.")
                return
            bot.reply_to(
                message,
                f"💵 **{amount:,} دولار أمريكي:**\n"
                f"🇹🇷 `{round(amount * res['TRY'], 2):,}` ليرة تركية\n"
                f"🇪🇺 `{round(amount * res['EUR'], 2):,}` يورو",
                parse_mode="Markdown"
            )
        except ValueError:
            bot.reply_to(message, "أرسل `/start` لعرض الأسعار، أو اكتب رقماً بالدولار (مثل `100`).")

    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
        
    return "Bot Running!", 200
