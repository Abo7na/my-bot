import os
import time
import requests
from flask import Flask, request
import telebot
from telebot import types

app = Flask(__name__)

# ذاكرة مؤقتة بسيطة للبيانات والإعدادات (تدعم التشغيل على Vercel)
user_mode = {}
custom_syp = {"buy": 149.50, "sell": 150.00, "official": 122.50}
admin_contacts = ["+963 900 000 000 (الإدارة العامة)"]
subscribers = set() # لحفظ معرفات المستخدمين للإذاعة
user_alerts = {} # لتنبيهات الأسعار

CHANNEL_USERNAME = "@DCo_Sy"
CHANNEL_URL = "https://t.me/DCo_Sy"

def get_all_prices():
    data = {
        "syp_buy_new": custom_syp["buy"],
        "syp_sell_new": custom_syp["sell"],
        "syp_official_new": custom_syp["official"],
        "try_rate": 2.94,
        "eur_usd": 163.00,
        "egp_rate": 2.75,
        "sar_rate": 39.45,
        "gold_oz": 3900.0,
        "change_pct": "0.34%+",
        "time_str": "14:36 (17/11)"
    }

    try:
        host = "cdn." + "jsdelivr" + ".net"
        path = "/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"
        r = requests.get("https://" + host + path, timeout=2.0)
        if r.status_code == 200:
            usd = r.json().get("usd", {})
            if usd.get("try"):
                data["try_rate"] = round(float(usd["try"]), 2)
            if usd.get("eur"):
                data["eur_usd"] = round(float(usd["eur"]), 2)
            if usd.get("egp"):
                data["egp_rate"] = round(float(usd["egp"]), 2)
            if usd.get("sar"):
                data["sar_rate"] = round(float(usd["sar"]), 2)
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

def check_subscription(bot, user_id):
    try:
        member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if member.status in ['member', 'creator', 'administrator']:
            return True
    except Exception:
        pass
    return False

def main_keyboard(bot_username=""):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 تحديث النشرة", callback_data="refresh"),
        types.InlineKeyboardButton("🧮 حاسبة العملات", callback_data="calc_menu"),
        types.InlineKeyboardButton("🪙 حاسبة الذهب", callback_data="gold_calc"),
        types.InlineKeyboardButton("📞 تواصل مع المشرف", callback_data="contact_admin"),
        types.InlineKeyboardButton("💡 دعم البوت", callback_data="support_bot"),
        types.InlineKeyboardButton("📢 قناة البوت", url=CHANNEL_URL),
        types.InlineKeyboardButton("📤 مشاركة البوت", url=f"https://t.me/share/url?url=https://t.me/{bot_username}&text=أفضل+بوت+لأسعار+الصرف+والعملات+في+سوريا!")
    )
    return markup

def format_bulletin(d, updated=False):
    buy_old = int(d["syp_buy_new"] * 100)
    sell_old = int(d["syp_sell_new"] * 100)
    
    return (
        "🌐 **الليرة اليوم - سوريا (عام)**[cite: 1]\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🇺🇸 **سعر الدولار الأمريكي**\n"
        f"• مبيع: `{d['syp_sell_new']:.2f}` ({sell_old:,} قديمة)\n"
        f"• شراء: `{d['syp_buy_new']:.2f}` ({buy_old:,} قديمة)\n"
        f"• مباشر 🟢 ({d['time_str']}) | {d['change_pct']} 📈\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🇹🇷 **TRY (تركي):** `{d['try_rate']}`  |  🇪🇺 **EUR (يورو):** `{d['eur_usd']}`\n"
        f"🇪🇬 **EGP (مصري):** `{d['egp_rate']}`  |  🇸🇦 **SAR (سعودي):** `{d['sar_rate']}`\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🪙 **أسعار الذهب:**\n"
        f"• أونصة عالمياً: `${d['gold_oz']:,.1f}`\n"
        f"• غرام 21 (سوري): `{d['gold_21_syp_new']:,.0f}` ل.س (`{d['gold_21_syp_old']:,}` قديمة)\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👇 اختر إحدى الخدمات أدناه:"
    )

@app.route('/', methods=['POST', 'GET'])
def webhook():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        return "BOT_TOKEN missing", 500
        
    bot = telebot.TeleBot(token, threaded=False)
    try:
        bot_info = bot.get_me()
        bot_username = bot_info.username
    except Exception:
        bot_username = "SyriaRatesBot"

    @bot.message_handler(commands=['start', 'prices'])
    def send_welcome(message):
        uid = message.from_user.id
        subscribers.add(uid)
        
        # فحص الاشتراك الإجباري
        if not check_subscription(bot, uid):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📢 اشترك في القناة الآن", url=CHANNEL_URL))
            markup.add(types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub"))
            bot.send_message(
                message.chat.id,
                "⚠️ **عذراً، يجب عليك الاشتراك في قناة البوت أولاً لتتمكن من استخدامه والاستفادة من نشرات الأسعار والخدمات!**\n\nرابط القناة: " + CHANNEL_URL,
                parse_mode="Markdown",
                reply_markup=markup
            )
            return

        user_mode[uid] = "usd_syp"
        d = get_all_prices()
        bot.send_message(message.chat.id, format_bulletin(d), parse_mode="Markdown", reply_markup=main_keyboard(bot_username))

    @bot.message_handler(commands=['asmaa1993'])
    def admin_panel(message):
        uid = message.from_user.id
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ إضافة رقم تواصل جديد", callback_data="admin_add_contact"),
            types.InlineKeyboardButton("📋 عرض أرقام التواصل الحالية", callback_data="admin_list_contacts"),
            types.InlineKeyboardButton("📢 إرسال إذاعة عامة للمستخدمين", callback_data="admin_broadcast"),
            types.InlineKeyboardButton("📊 إحصائيات البوت", callback_data="admin_stats")
        )
        bot.send_message(message.chat.id, "🛠 **أهلاً بك في لوحة تحكم المشرف (الإدارة):**", parse_mode="Markdown", reply_markup=markup)

    @bot.message_handler(commands=['set'])
    def set_rate(message):
        uid = message.from_user.id
        if not check_subscription(bot, uid):
            return
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
        uid = call.from_user.id

        if call.data == "check_sub":
            if check_subscription(bot, uid):
                bot.answer_callback_query(call.id, "✅ تم التحقق من اشتراكك بنجاح!")
                d = get_all_prices()
                bot.edit_message_text(format_bulletin(d), cid, call.message.message_id, parse_mode="Markdown", reply_markup=main_keyboard(bot_username))
            else:
                bot.answer_callback_query(call.id, "❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)
            return

        if not check_subscription(bot, uid):
            bot.answer_callback_query(call.id, "⚠️ يجب الاشتراك في القناة أولاً!", show_alert=True)
            return

        if call.data == "refresh":
            d = get_all_prices()
            try:
                bot.edit_message_text(format_bulletin(d, True), cid, call.message.message_id, parse_mode="Markdown", reply_markup=main_keyboard(bot_username))
            except Exception:
                pass
            bot.answer_callback_query(call.id, "✅ تم التحديث!")

        elif call.data == "calc_menu":
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🇺🇸 دولار ⬅️ 🇸🇾 سوري", callback_data="mode_usd_syp"),
                types.InlineKeyboardButton("🇸🇾 سوري ⬅️ 🇺🇸 دولار", callback_data="mode_syp_usd"),
                types.InlineKeyboardButton("🇹🇷 تركي ⬅️ 🇸🇾 سوري", callback_data="mode_try_syp"),
                types.InlineKeyboardButton("🇪🇺 يورو ⬅️ 🇸🇾 سوري", callback_data="mode_eur_syp"),
                types.InlineKeyboardButton("🔙 العودة", callback_data="refresh")
            )
            bot.edit_message_text("🧮 **حاسبة تحويل العملات التفاعلية**\n\nاختر اتجاه التحويل ثم أرسل المبلغ كرقم:", cid, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            bot.answer_callback_query(call.id)

        elif call.data.startswith("mode_"):
            mode = call.data.replace("mode_", "")
            user_mode[uid] = mode
            bot.send_message(cid, "✍️ أرسل الآن **المبلغ** كرقم فقط (مثلاً: `100`):", parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        elif call.data == "gold_calc":
            user_mode[uid] = "gold_calc"
            bot.send_message(cid, "🪙 **حاسبة الذهب الذكية**\n\nأرسل عدد غرامات الذهب (مثلاً: `5` لعيار 21):", parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        elif call.data == "contact_admin":
            contacts_text = "\n".join([f"• {c}" for c in admin_contacts])
            bot.send_message(cid, f"📞 **أرقام وطرق التواصل مع الإدارة والمشرفين:**\n\n{contacts_text}\n\nيمكنك أيضاً إرسال رسالتك هنا وسنقوم بالرد عليك في أقرب وقت.", parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        elif call.data == "support_bot":
            bot.send_message(cid, "💡 **دعم وتطوير البوت**\n\nنرحب بدعمكم المستمر لاستمرار البوت وتحديث الأسعار لحظياً ودون توقف.\nللتبرع أو المساهمة في تطوير المشروع، يرجى التواصل عبر زر (تواصل مع المشرف). شكراً لثقتكم!", parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        elif call.data == "admin_list_contacts":
            contacts_text = "\n".join([f"{i+1}. {c}" for i, c in enumerate(admin_contacts)])
            bot.answer_callback_query(call.id)
            bot.send_message(cid, f"📋 **قائمة أرقام التواصل الحالية:**\n\n{contacts_text}", parse_mode="Markdown")

        elif call.data == "admin_add_contact":
            user_mode[uid] = "waiting_for_contact"
            bot.send_message(cid, "✍️ أرسل الآن رقم أو تفاصيل التواصل الجديدة لإضافتها لقائمة المشرفين:", parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        elif call.data == "admin_stats":
            bot.answer_callback_query(call.id)
            bot.send_message(cid, f"📊 **إحصائيات البوت:**\n\n• عدد المستخدمين المسجلين: `{len(subscribers)}` مستخدم", parse_mode="Markdown")

        elif call.data == "admin_broadcast":
            user_mode[uid] = "waiting_for_broadcast"
            bot.send_message(cid, "📢 أرسل الآن نص الإذاعة أو الإعلان الذي تريد إرساله لجميع المستخدمين:", parse_mode="Markdown")
            bot.answer_callback_query(call.id)

    @bot.message_handler(func=lambda message: True)
    def handle_messages(message):
        cid = message.chat.id
        uid = message.from_user.id
        subscribers.add(uid)

        if not check_subscription(bot, uid):
            return

        mode = user_mode.get(uid, "usd_syp")
        text = message.text.strip()

        # التعامل مع أوامر المشرف للإضافة أو الإذاعة
        if mode == "waiting_for_contact":
            admin_contacts.append(text)
            user_mode[uid] = "usd_syp"
            bot.reply_to(message, "✅ تمت إضافة رقم التواصل بنجاح إلى لوحة التحكم!")
            return

        if mode == "waiting_for_broadcast":
            user_mode[uid] = "usd_syp"
            success_count = 0
            for sub_id in subscribers:
                try:
                    bot.send_message(sub_id, f"📢 **إعلان هام من الإدارة:**\n\n{text}", parse_mode="Markdown")
                    success_count += 1
                except Exception:
                    pass
            bot.reply_to(message, f"✅ تم إرسال الإذاعة بنجاح إلى `{success_count}` مستخدم.")
            return

        if mode == "gold_calc":
            try:
                grams = float(text.replace(",", ""))
                d = get_all_prices()
                total_new = grams * d["gold_21_syp_new"]
                total_old = int(total_new * 100)
                total_usd = grams * d["gold_21_usd"]
                reply = (
                    f"🪙 **قيمة {grams} غرام ذهب (عيار 21):**\n"
                    f"• بالليرة الجديدة: `{total_new:,.2f}` ل.س\n"
                    f"• بالليرة القديمة: `{total_old:,}` ل.س\n"
                    f"• بالدولار الأمريكي: `${total_usd:,.2f}`"
                )
                bot.reply_to(message, reply, parse_mode="Markdown")
            except ValueError:
                bot.reply_to(message, "⚠️ يرجى إرسال رقم صحيح لعدد الغرامات (مثلاً: `5`).")
            return

        # حاسبة العملات العادية
        try:
            amount = float(text.replace(",", ""))
            d = get_all_prices()
            rate_new = d["syp_sell_new"]

            if mode == "usd_syp":
                res_new = amount * rate_new
                res_old = int(res_new * 100)
                reply = f"💵 **{amount:,} دولار يساوي:**\n• بالجديدة: `{res_new:,.2f}` ل.س\n• بالقديمة: `{res_old:,}` ل.س"
            elif mode == "syp_usd":
                usd_val = amount / (rate_new * 100) if amount >= 2000 else amount / rate_new
                reply = f"🇸🇾 **{amount:,.0f} ليرة** تساوي:\n💵 **`{usd_val:,.2f}` دولار أمريكي**"
            elif mode == "try_syp":
                try_in_syp = rate_new / d["try_rate"]
                res_new = amount * try_in_syp
                reply = f"🇹🇷 **{amount:,} ليرة تركية تساوي:**\n• بالجديدة: `{res_new:,.2f}` ل.س"
            elif mode == "eur_syp":
                eur_in_syp = rate_new * d["eur_usd"] / 100 # تقريبي للتوافق
                res_new = amount * eur_in_syp
                reply = f"🇪🇺 **{amount:,} يورو يساوي:**\n• بالجديدة: `{res_new:,.2f}` ل.س"
            else:
                res_new = amount * rate_new
                reply = f"💵 **{amount:,} يساوي:** `{res_new:,.2f}` ل.س جديد"

            bot.reply_to(message, reply, parse_mode="Markdown")
        except ValueError:
            bot.reply_to(message, "⚠️ يرجى إرسال رقم صحيح للتحويل أو استخدام الأزرار في القائمة الرئيسية.")

    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
        
    return "Syria Rates Bot Pro is Running!", 200
