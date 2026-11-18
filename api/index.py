import os
import requests
from flask import Flask, request
import telebot
from telebot import types

app = Flask(__name__)

def get_rates():
    try:
        # جلب أسعار العملات مقابل الدولار
        res = requests.get("https://er-api.com", timeout=5).json()
        rates = res["rates"]
        
        # جلب سعر الذهب (XAU) والبيتكوين (BTC) من CoinGecko
        crypto = requests.get(
            "https://coingecko.com",
            timeout=5
        ).json()
        
        btc_price = crypto["bitcoin"]["usd"]
        gold_oz = crypto["pax-gold"]["usd"]
        gold_24 = round(gold_oz / 31.1035, 2)
        gold_21 = round(gold_24 * 0.875, 2)
        
        return {
            "EUR": round(rates["EUR"], 4),
            "TRY": round(rates["TRY"], 2),
            "SAR": round(rates["SAR"], 2),
            "AED": round(rates["AED"], 2),
            "EGP": round(rates["EGP"], 2),
            "JOD": round(rates["JOD"], 3),
            "BTC": f"{btc_price:,}",
            "GOLD_OZ": f"{gold_oz:,}",
            "GOLD_24": gold_24,
            "GOLD_21": gold_21
        }
    except Exception as e:
        return None

@app.route('/', methods=['POST', 'GET'])
def webhook():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        return "BOT_TOKEN missing", 500
        
    bot = telebot.TeleBot(token, threaded=False)

    @bot.message_handler(commands=['start', 'prices'])
    def send_prices(message):
        markup = types.InlineKeyboardMarkup()
        btn_refresh = types.InlineKeyboardButton("🔄 تحديث الأسعار الآن", callback_data="refresh")
        markup.add(btn_refresh)
        
        data = get_rates()
        if not data:
            bot.reply_to(message, "⚠️ تعذر جلب الأسعار حالياً، حاول بعد قليل.")
            return
            
        text = (
            "💱 **نشرة أسعار الصرف والذهب اللحظية**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🇪🇺 **اليورو (EUR):** `{data['EUR']}` دولار\n"
            f"🇹🇷 **الليرة التركية:** `{data['TRY']}` ليرة\n"
            f"🇸🇦 **الريال السعودي:** `{data['SAR']}` ريال\n"
            f"🇦🇪 **الدرهم الإماراتي:** `{data['AED']}` درهم\n"
            f"🇪🇬 **الجنيه المصري:** `{data['EGP']}` جنيه\n"
            f"🇯🇴 **الدينار الأردني:** `{data['JOD']}` دينار\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🪙 **أونصة الذهب:** `${data['GOLD_OZ']}`\n"
            f"✨ **غرام ذهب 24:** `${data['GOLD_24']}`\n"
            f"✨ **غرام ذهب 21:** `${data['GOLD_21']}`\n"
            f"₿ **البيتكوين:** `${data['BTC']}`\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💡 *أرسل أي رقم (مثلاً: 100) لتحويله من الدولار إلى باقي العملات!*"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "refresh")
    def callback_refresh(call):
        data = get_rates()
        if data:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 تحديث الأسعار الآن", callback_data="refresh"))
            text = (
                "💱 **نشرة أسعار الصرف والذهب اللحظية (محدّثة)**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🇪🇺 **اليورو (EUR):** `{data['EUR']}` دولار\n"
                f"🇹🇷 **الليرة التركية:** `{data['TRY']}` ليرة\n"
                f"🇸🇦 **الريال السعودي:** `{data['SAR']}` ريال\n"
                f"🇦🇪 **الدرهم الإماراتي:** `{data['AED']}` درهم\n"
                f"🇪🇬 **الجنيه المصري:** `{data['EGP']}` جنيه\n"
                f"🇯🇴 **الدينار الأردني:** `{data['JOD']}` دينار\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🪙 **أونصة الذهب:** `${data['GOLD_OZ']}`\n"
                f"✨ **غرام ذهب 24:** `${data['GOLD_24']}`\n"
                f"✨ **غرام ذهب 21:** `${data['GOLD_21']}`\n"
                f"₿ **البيتكوين:** `${data['BTC']}`\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "💡 *أرسل أي رقم لتحويله من الدولار فوراً!*"
            )
            try:
                bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            except:
                pass
        bot.answer_callback_query(call.id, "✅ تم تحديث الأسعار!")

    @bot.message_handler(func=lambda message: True)
    def convert_amount(message):
        try:
            amount = float(message.text.strip())
            res = requests.get("https://er-api.com", timeout=5).json()["rates"]
            reply = (
                f"💵 **تحويل مبلغ ${amount:,} دولار أمريكي:**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🇹🇷 **تركي:** `{round(amount * res['TRY'], 2):,}` ليرة\n"
                f"🇸🇦 **سعودي:** `{round(amount * res['SAR'], 2):,}` ريال\n"
                f"🇦🇪 **إماراتي:** `{round(amount * res['AED'], 2):,}` درهم\n"
                f"🇪🇬 **مصري:** `{round(amount * res['EGP'], 2):,}` جنيه\n"
                f"🇪🇺 **يورو:** `{round(amount * res['EUR'], 2):,}` يورو"
            )
            bot.reply_to(message, reply, parse_mode="Markdown")
        except ValueError:
            bot.reply_to(message, "أرسل `/start` لعرض نشرة الأسعار، أو أرسل رقماً فقط (مثل `50`) لتحويله.")

    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
        
    return "Exchange Rate Bot is Running!", 200
