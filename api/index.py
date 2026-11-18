import os
import requests
from flask import Flask, request
import telebot
from telebot import types

app = Flask(__name__)

def get_rates():
    try:
        # تجميع الرابط برمجياً لحمايته من القصّ أثناء النسخ
        host = "cdn." + "jsdelivr" + ".net"
        path = "/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"
        url = "https://" + host + path
        
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            usd = r.json().get("usd", {})
            return {
                "SYP": round(float(usd.get("syp", 0)), 2),
                "TRY": round(float(usd.get("try", 0)), 2),
                "SAR": round(float(usd.get("sar", 0)), 2),
                "AED": round(float(usd.get("aed", 0)), 2),
                "EGP": round(float(usd.get("egp", 0)), 2),
                "JOD": round(float(usd.get("jod", 0)), 3),
                "EUR": round(float(usd.get("eur", 0)), 4)
            }
        return f"Status: {r.status_code}"
    except Exception as e:
        return f"Err: {str(e)}"

def format_msg(res, updated=False):
    header = "💱 **نشرة أسعار الصرف اليوم (محدّثة)**" if updated else "💱 **نشرة أسعار الصرف اليوم**"
    return (
        f"{header}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🇸🇾 **الليرة السورية (رسمي):** `{res['SYP']:,.0f}` ل.س\n"
        f"🇹🇷 **الليرة التركية:** `{res['TRY']}` ليرة\n"
        f"🇸🇦 **الريال السعودي:** `{res['SAR']}` ريال\n"
        f"🇦🇪 **الدرهم الإماراتي:** `{res['AED']}` درهم\n"
        f"🇪🇬 **الجنيه المصري:** `{res['EGP']}` جنيه\n"
        f"🇯🇴 **الدينار الأردني:** `{res['JOD']}` دينار\n"
        f"🇪🇺 **اليورو (EUR):** `{res['EUR']}` دولار\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💡 *أرسل أي مبلغ بالدولار (مثلاً: 100) لتحويله فوراً!*"
    )

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
        bot.send_message(message.chat.id, format_msg(res), parse_mode="Markdown", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "refresh")
    def callback_refresh(call):
        res = get_rates()
        if not isinstance(res, str):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 تحديث الأسعار", callback_data="refresh"))
            try:
                bot.edit_message_text(format_msg(res, True), call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
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
            reply = (
                f"💵 **تحويل {amount:,} دولار أمريكي:**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🇸🇾 `{int(amount * res['SYP']):,}` ليرة سورية\n"
                f"🇹🇷 `{round(amount * res['TRY'], 2):,}` ليرة تركية\n"
                f"🇸🇦 `{round(amount * res['SAR'], 2):,}` ريال سعودي\n"
                f"🇦🇪 `{round(amount * res['AED'], 2):,}` درهم إماراتي\n"
                f"🇪🇬 `{round(amount * res['EGP'], 2):,}` جنيه مصري\n"
                f"🇪🇺 `{round(amount * res['EUR'], 2):,}` يورو"
            )
            bot.reply_to(message, reply, parse_mode="Markdown")
        except ValueError:
            bot.reply_to(message, "أرسل `/start` لعرض النشرة، أو اكتب رقماً بالدولار (مثل `50`).")

    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
        
    return "SYP Currency Bot Running!", 200
