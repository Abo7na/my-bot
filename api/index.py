import os
import re
import json
import urllib.request
from flask import Flask, request
import telebot
from telebot import types

app = Flask(__name__)

def fetch_rates():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ar,en-US;q=0.9,en;q=0.8"
    }
    
    # المحاولة 1: جلب أسعار الصرف من Google Finance (موثوق 100% ولا يحظر السيرفرات أبداً)
    try:
        def get_google_rate(pair):
            url = f"https://google.com{pair}"
            req = urllib.request.Request(url, headers=headers)
            html = urllib.request.urlopen(req, timeout=5).read().decode("utf-8", errors="ignore")
            match = re.search(r'data-last-price="([0-9.,]+)"', html)
            if match:
                return float(match.group(1).replace(",", ""))
            return None

        syp = get_google_rate("USD-SYP")
        try_rate = get_google_rate("USD-TRY")
        eur_usd = get_google_rate("EUR-USD")
        sar = get_google_rate("USD-SAR")
        
        if syp:
            return {
                "source": "Google Finance",
                "SYP": syp,
                "TRY": round(try_rate, 2) if try_rate else "-",
                "EUR": round(eur_usd, 4) if eur_usd else "-",
                "SAR": round(sar, 2) if sar else "-"
            }
    except Exception as e:
        return f"خطأ في الاتصال: {str(e)}"
        
    return "لم يتم العثور على السعر في الصفحة"

@app.route('/', methods=['POST', 'GET'])
def webhook():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        return "BOT_TOKEN missing", 500
        
    bot = telebot.TeleBot(token, threaded=False)

    @bot.message_handler(commands=['start', 'syp'])
    def send_price(message):
        res = fetch_rates()
        if isinstance(res, str):
            bot.reply_to(message, f"⚠️ `{res}`", parse_mode="Markdown")
            return
            
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔄 تحديث الأسعار الآن", callback_data="refresh"))
        
        text = (
            "💱 **نشرة أسعار الصرف اللحظية**\n"
            "━━━━━━━━━━━━━━━━━━\n"
            f"🇸🇾 **1 دولار أمريكي:** `{res['SYP']:,.0f}` ل.س\n"
            f"🇹🇷 **1 دولار أمريكي:** `{res['TRY']}` ليرة تركية\n"
            f"🇸🇦 **1 دولار أمريكي:** `{res['SAR']}` ريال سعودي\n"
            f"🇪🇺 **1 يورو:** `{res['EUR']}` دولار\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "💡 *أرسل أي مبلغ بالدولار (مثلاً: 100) لتحويله إلى الليرة السورية فوراً!*"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "refresh")
    def callback_refresh(call):
        res = fetch_rates()
        if not isinstance(res, str):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 تحديث الأسعار الآن", callback_data="refresh"))
            text = (
                "💱 **نشرة أسعار الصرف اللحظية (محدّثة)**\n"
                "━━━━━━━━━━━━━━━━━━\n"
                f"🇸🇾 **1 دولار أمريكي:** `{res['SYP']:,.0f}` ل.س\n"
                f"🇹🇷 **1 دولار أمريكي:** `{res['TRY']}` ليرة تركية\n"
                f"🇸🇦 **1 دولار أمريكي:** `{res['SAR']}` ريال سعودي\n"
                f"🇪🇺 **1 يورو:** `{res['EUR']}` دولار\n"
                "━━━━━━━━━━━━━━━━━━\n"
                "💡 *أرسل أي مبلغ بالدولار لتحويله إلى الليرة السورية فوراً!*"
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
            res = fetch_rates()
            if isinstance(res, str):
                bot.reply_to(message, "⚠️ تعذر جلب السعر للتحويل.")
                return
            total_syp = int(amount * res["SYP"])
            bot.reply_to(
                message,
                f"💵 **{amount:,} دولار** = `{total_syp:,}` ليرة سورية",
                parse_mode="Markdown"
            )
        except ValueError:
            bot.reply_to(message, "أرسل `/start` لعرض الأسعار، أو اكتب رقماً بالدولار (مثل `50`) لتحويله.")

    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
        
    return "Google Finance Bot is Running!", 200
