import os
import requests
from flask import Flask, request
import telebot
from telebot import types

app = Flask(__name__)

# ذاكرة مؤقتة لوضع التحويل والسعر المتداول
user_mode = {}
custom_syp = {"buy": 149.50, "sell": 150.00, "official": 122.50}

def get_all_prices():
    data = {
        "syp_buy_new": custom_syp["buy"],
        "syp_sell_new": custom_syp["sell"],
        "syp_official_new": custom_syp["official"],
        "try_rate": 50.40,
        "eur_usd": 1.10,
        "gold_oz": 3900.0
    }

    # جلب الأسعار العالمية والذهب من شبكة jsDelivr السريعة جداً (مهلة ثانيتين فقط)
    try:
        host = "cdn." + "jsdelivr" + ".net"
        path = "/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"
        r = requests.get("https://" + host + path, timeout=2.5)
        if r.status_code == 200:
            usd = r.json().get("usd", {})
            if usd.get("try"):
                data["try_rate"] = round(float(usd["try"]), 2)
            if usd.get("eur"):
                data["eur_usd"] = round(1 / float(usd["eur"]), 4)
            if usd.get("xau"):
                data["gold_oz"] = round(1 / float(usd["xau"]), 2)
    except Exception:
        pass

    gold_24_usd = data["gold_oz"] / 31.1035
    gold_21_usd = gold_24_usd * 0.875
    data["gold_24_usd"] = round(gold_24_usd, 2)
    data["gold_21_usd"] = round(gold_21_usd, 2)
    data["gold_21_syp_new"] = round(gold_21_usd * data["syp_sell_new"], 2)
    data["gold_21_syp_old"] = int(data["gold_21_syp_new"] * 100)

    return data

def main_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 تحديث النشرة", callback_data="refresh"),
        types.InlineKeyboardButton("🧮 حاسبة التحويل", callback_data="calc_menu")
    )
    return markup

def calc_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇺🇸 دولار ⬅️ 🇸🇾 سوري", callback_data="mode_usd_syp"),
        types.InlineKeyboardButton("🇸🇾 سوري ⬅️ 🇺🇸 دولار", callback_data="mode_syp_usd"),
        types.InlineKeyboardButton("🇹🇷 تركي ⬅️ 🇸🇾 سوري", callback_data="mode_try_syp"),
        types.InlineKeyboardButton("🇪🇺 يورو ⬅️ 🇸🇾 سوري", callback_data="mode_eur_syp"),
        types.InlineKeyboardButton("🔙 العودة للنشرة", callback_data="refresh")
    )
    return markup

def format_bulletin(d, updated=False):
    title = "💱 **نشرة الأسعار في سوريا (محدّثة)**" if updated else "💱 **نشرة الأسعار في سوريا اليوم**"
    buy_old = int(d["syp_buy_new"] * 100)
    sell_old = int(d["syp_sell_new"] * 100)
    off_old = int(d["syp_official_new"] * 100)
    
    return (
        f"{title}\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🇺🇸 **الدولار (السوق المتداول):**\n"
        f"• شراء: `{d['syp_buy_new']:.2f}` جديدة (`{buy_old:,}` قديمة)\n"
        f"• مبيع: `{d['syp_sell_new']:.2f}` جديدة (`{sell_old:,}` قديمة)\n\n"
        "🏛 **الدولار (النشرة الرسمية):**\n"
        f"• السعر: `{d['syp_official_new']:.2f}` جديدة (`{off_old:,}` قديمة)\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🌍 **العملات الأجنبية (لحظي):**\n"
        f"• 🇪🇺 اليورو: `{d['eur_usd']}` دولار\n"
        f"• 🇹🇷 الدولار مقابل التركي: `{d['try_rate']}` ليرة\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🪙 **أسعار الذهب (لحظي):**\n"
        f"• الأونصة عالمياً: `${d['gold_oz']:,.1f}`\n"
        f"• غرام 24: `${d['gold_24_usd']}` | غرام 21: `${d['gold_21_usd']}`\n"
        f"• غرام 21 (سوري): `{d['gold_21_syp_new']:,.0f}` جديدة (`{d['gold_21_syp_old']:,}` قديمة)\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💡 *اضغط (🧮 حاسبة التحويل) للتحويل بين العملات!*"
    )

@app.route('/', methods=['POST', 'GET'])
def webhook():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        return "BOT_TOKEN missing", 500
        
    bot = telebot.TeleBot(token, threaded=False)

    @bot.message_handler(commands=['start', 'prices'])
    def send_welcome(message):
        user_mode[message.chat.id] = "usd_syp"
        d = get_all_prices()
        bot.send_message(message.chat.id, format_bulletin(d), parse_mode="Markdown", reply_markup=main_keyboard())

    @bot.message_handler(commands=['set'])
    def set_rate(message):
        try:
            parts = message.text.split()
            val = float(parts[1])
            if val > 1000:
                val = val / 100.0
            custom_syp["sell"] = val
            custom_syp["buy"] = round(val - 0.5, 2)
            bot.reply_to(message, f"✅ تم تحديث سعر الدولار المتداول إلى `{val:.2f}` جديدة (`{int(val*100):,}` قديمة).", parse_mode="Markdown")
        except Exception:
            bot.reply_to(message, "اكتب الأمر متبوعاً بالسعر الجديد، مثلاً:\n`/set 150` أو `/set 15000`", parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callbacks(call):
        cid = call.message.chat.id
        if call.data == "refresh":
            d = get_all_prices()
            try:
                bot.edit_message_text(format_bulletin(d, True), cid, call.message.message_id, parse_mode="Markdown", reply_markup=main_keyboard())
            except Exception:
                pass
            bot.answer_callback_query(call.id, "✅ تم التحديث!")

        elif call.data == "calc_menu":
            bot.edit_message_text(
                "🧮 **حاسبة تحويل العملات التفاعلية**\n\nاختر اتجاه التحويل المطلوب من الأزرار بالأسفل، ثم أرسل المبلغ كرقم:",
                cid, call.message.message_id, parse_mode="Markdown", reply_markup=calc_keyboard()
            )
            bot.answer_callback_query(call.id)

        elif call.data.startswith("mode_"):
            mode = call.data.replace("mode_", "")
            user_mode[cid] = mode
            names = {
                "usd_syp": "🇺🇸 الدولار ⬅️ 🇸🇾 الليرة السورية",
                "syp_usd": "🇸🇾 الليرة السورية ⬅️ 🇺🇸 الدولار",
                "try_syp": "🇹🇷 الليرة التركية ⬅️ 🇸🇾 الليرة السورية",
                "eur_syp": "🇪🇺 اليورو ⬅️ 🇸🇾 الليرة السورية"
            }
            bot.send_message(
                cid,
                f"✅ تم اختيار: **{names.get(mode)}**\n\n✍️ أرسل الآن **المبلغ** كرقم (مثلاً: `100`):",
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)

    @bot.message_handler(func=lambda message: True)
    def handle_amount(message):
        cid = message.chat.id
        try:
            amount = float(message.text.strip().replace(",", ""))
            d = get_all_prices()
            rate_new = d["syp_sell_new"]
            mode = user_mode.get(cid, "usd_syp")

            if mode == "usd_syp":
                res_new = amount * rate_new
                res_old = int(res_new * 100)
                reply = (
                    f"💵 **{amount:,} دولار أمريكي يساوي:**\n"
                    f"• بالليرة الجديدة: `{res_new:,.2f}` ل.س\n"
                    f"• بالليرة القديمة: `{res_old:,}` ل.س"
                )
            elif mode == "syp_usd":
                if amount >= 2000:
                    usd_val = amount / (rate_new * 100)
                    label = "ليرة قديمة"
                else:
                    usd_val = amount / rate_new
                    label = "ليرة جديدة"
                reply = f"🇸🇾 **{amount:,.0f} {label}** تساوي:\n💵 **`{usd_val:,.2f}` دولار أمريكي**"
            elif mode == "try_syp":
                try_in_syp_new = rate_new / d["try_rate"]
                res_new = amount * try_in_syp_new
                res_old = int(res_new * 100)
                reply = (
                    f"🇹🇷 **{amount:,} ليرة تركية تساوي:**\n"
                    f"• بالليرة الجديدة: `{res_new:,.2f}` ل.س\n"
                    f"• بالليرة القديمة: `{res_old:,}` ل.س"
                )
            elif mode == "eur_syp":
                eur_in_syp_new = rate_new * d["eur_usd"]
                res_new = amount * eur_in_syp_new
                res_old = int(res_new * 100)
                reply = (
                    f"🇪🇺 **{amount:,} يورو يساوي:**\n"
                    f"• بالليرة الجديدة: `{res_new:,.2f}` ل.س\n"
                    f"• بالليرة القديمة: `{res_old:,}` ل.س"
                )

            bot.reply_to(message, reply, parse_mode="Markdown", reply_markup=calc_keyboard())
        except ValueError:
            bot.reply_to(message, "⚠️ يرجى إدخال رقم صحيح للتحويل (مثلاً: `100`)، أو أرسل `/start` للقائمة الرئيسية.")

    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
        
    return "Fast Syria Gold & Currency Bot is Running!", 200
