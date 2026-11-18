import os
import requests
from flask import Flask, request
import telebot
from telebot import types

app = Flask(__name__)

def get_rates():
    data = {}
    headers = {"User-Agent": "Mozilla/5.0"}
    
    # 1. جلب أسعار العملات
    try:
        res = requests.get("https://er-api.com", headers=headers, timeout=5).json()
        rates = res.get("rates", {})
        data["SYP"] = f"{int(rates.get('SYP', 0)):,}"
        data["TRY"] = round(rates.get("TRY", 0), 2)
        data["SAR"] = round(rates.get("SAR", 0), 2)
        data["AED"] = round(rates.get("AED", 0), 2)
        data["EGP"] = round(rates.get("EGP", 0), 2)
        data["JOD"] = round(rates.get("JOD", 0), 3)
        data["EUR"] = round(rates.get("EUR", 0), 4)
        data["raw_rates"] = rates
    except Exception:
        return None

    # 2. جلب البيتكوين والذهب من مصدر بديل لا يحظر السيرفرات
    try:
        btc_res = requests.get("https://coinbase.com", headers=headers, timeout=4).json()
        btc_price = float(btc_res["data"]["amount"])
        data["BTC"] = f"{int(btc_price):,}"
    except Exception:
        data["BTC"] = "غير متاح"

    try:
        # سعر أونصة الذهب (PAXG يساوي أونصة ذهب حقيقية)
        gold_res = requests.get("https://coinbase.com", headers=headers, timeout=4).json()
        gold_oz = float(gold_res["data"]["amount"])
        gold_24 = round(gold_oz / 31.1035, 2)
        gold_21 = round(gold_24 * 0.875, 2)
        data["GOLD_OZ"] = f"{round(gold_oz, 1):,}"
        data["GOLD_24"] = gold_24
        data["GOLD_21"] = gold_21
    except Exception:
        data["GOLD_OZ"] = "غير متاح"
        data["GOLD_24"] = "-"
        data["GOLD_21"] = "-"

    return data

def format_message(data, updated=False):
    title = "💱 **نشرة أسعار الصرف والذهب (محدّثة)**" if updated else "💱 **نشرة أسعار الصرف والذهب اللحظية**"
    return (
        f"{title}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🇸🇾 **الليرة السورية (رسمي):** `{data['SYP']}` ل.س\n"
        f"🇹🇷 **الليرة التركية:** `{data['TRY']}` ليرة\n"
        f"🇸🇦 **الريال السعودي:** `{data['SAR']}` ريال\n"
        f"🇦🇪 **الدرهم الإماراتي:** `{data['AED']}` درهم\n"
        f"🇪🇬 **الجنيه المصري:** `{data['EGP']}` جنيه\n"
        f"🇯🇴 **الدينار الأردني:** `{data['JOD']}` دينار\n"
        f"🇪🇺 **اليورو (EUR):** `{data['EUR']}` دولار\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🪙 **أونصة الذهب:** `${data['GOLD_OZ']}`\n"
        f"✨ **غرام ذهب 24:** `${data['GOLD_24']}`\n"
        f"✨ **غرام ذهب 21:** `${data['GOLD_21']}`\n"
        f"₿ **البيتكوين:** `${data['BTC']}`\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💡 *أرسل أي رقم (مثلاً: 100) لتحويله من الدولار فوراً!*"
    )

@app.route('/', methods=['POST', 'GET'])
def webhook():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        return "BOT_TOKEN missing", 500
        
    bot = telebot.TeleBot(token, threaded=False)

    @bot.message_handler(commands=['start', 'prices'])
    def send_prices(message):
        data = get_rates()
        if not data:
            bot.reply_to(message, "⚠️ تعذر الاتصال بمصدر الأسعار، أعد المحاولة.")
            return
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 تحديث الأسعار الآن", callback_data="refresh"))
        bot.send_message(message.chat.id, format_message(data), parse_mode="Markdown", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "refresh")
    def callback_refresh(call):
        data = get_rates()
        if data:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 تحديث الأسعار الآن", callback_data="refresh"))
            try:
                bot.edit_message_text(format_message(data, True), call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            except Exception:
                pass
        bot.answer_callback_query(call.id, "✅ تم التحديث!")

    @bot.message_handler(func=lambda message: True)
    def convert_amount(message):
        try:
            amount = float(message.text.strip())
            data = get_rates()
            if not data:
                bot.reply_to(message, "⚠️ تعذر جلب الأسعار للتحويل.")
                return
            r = data["raw_rates"]
            reply = (
                f"💵 **تحويل مبلغ ${amount:,} دولار أمريكي:**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🇸🇾 **سوري:** `{int(amount * r['SYP']):,}` ل.س\n"
                f"🇹🇷 **تركي:** `{round(amount * r['TRY'], 2):,}` ليرة\n"
                f"🇸🇦 **سعودي:** `{round(amount * r['SAR'], 2):,}` ريال\n"
                f"🇦🇪 **إماراتي:** `{round(amount * r['AED'], 2):,}` درهم\n"
                f"🇪🇬 **مصري:** `{round(amount * r['EGP'], 2):,}` جنيه\n"
                f"🇪🇺 **يورو:** `{round(amount * r['EUR'], 2):,}` يورو"
            )
            bot.reply_to(message, reply, parse_mode="Markdown")
        except ValueError:
            bot.reply_to(message, "أرسل `/start` لعرض النشرة، أو اكتب رقماً فقط (مثل `50`) لتحويله.")

    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
        
    return "Exchange Rate Bot is Running!", 200
