import os
import time
import requests
from flask import Flask, request
import telebot
from telebot import types

app = Flask(__name__)

# تخزين مؤقت في الذاكرة (يدعم التشغيل السريع على Vercel)
user_mode = {}
custom_syp = {"buy": 149.50, "sell": 150.00, "official": 122.50}
support_tickets = []  # قائمة رسائل الدعم الواردة من المستخدمين
subscribers = set()   # المشتركون للإذاعة
referrals = {}        # تتبع الدعوات: {user_id: count}
price_alerts = {}     # التنبيهات السعرية: {user_id: target_price}
reply_target = {}     # لتخزين معرف المستخدم الذي يرد عليه المشرف

CHANNEL_USERNAME = "@DCo_Sy"
CHANNEL_URL = "https://" + "t." + "me/DCo_Sy"

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
        "time_str": time.strftime("%H:%M (%d/%m)")
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

def main_keyboard(bot_username="", user_id=0):
    ref_link = "https://" + "t." + f"me/{bot_username}?start=ref_{user_id}"
    share_url = "https://" + "t." + f"me/share/url?url={ref_link}&text=تابع+أسعار+الصرف+والذهب+لحظة+بلحظة+عبر+سوريا+كاش!"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 تحديث الأسعار", callback_data="refresh"),
        types.InlineKeyboardButton("🧮 حاسبة العملات", callback_data="calc_menu"),
        types.InlineKeyboardButton("🪙 حاسبة الذهب", callback_data="gold_calc"),
        types.InlineKeyboardButton("🔔 ضبط منبّه سعر", callback_data="set_alert"),
        types.InlineKeyboardButton("📩 تواصل مع المشرف", callback_data="contact_admin"),
        types.InlineKeyboardButton("💝 دعم وتطوير البوت", callback_data="support_bot"),
        types.InlineKeyboardButton("🏆 رابط الدعوة الخاص", callback_data="my_ref"),
        types.InlineKeyboardButton("📤 مشاركة النشرة", url=share_url)
    )
    return markup

def format_bulletin(d, updated=False):
    header = "💎 **سوريا كاش - Syria Cash** 💎"
    sub_header = "*(تحديث لحظي ومباشر لأسعار السوق)*" if updated else "*(نشرة أسعار الصرف والذهب في سوريا)*"
    buy_old = int(d["syp_buy_new"] * 100)
    sell_old = int(d["syp_sell_new"] * 100)
    
    return (
        f"{header}\n"
        f"{sub_header}\n"
        "╔════════════════════╗\n"
        "🇺🇸 **الدولار الأمريكي (سوريا - عام)**\n"
        f"🔹 **مبيع:** `{d['syp_sell_new']:.2f}` ل.س  |  (`{sell_old:,}` قديمة)\n"
        f"🔸 **شراء:** `{d['syp_buy_new']:.2f}` ل.س  |  (`{buy_old:,}` قديمة)\n"
        f"📡 الحالة: مباشر 🟢 `{d['time_str']}` ({d['change_pct']})\n"
        "╠════════════════════╣\n"
        "🌍 **أسعار العملات مقابل الدولار:**\n"
        f"🇪🇺 **اليورو (EUR):** `{d['eur_usd']}`   |   🇹🇷 **التركي (TRY):** `{d['try_rate']}`\n"
        f"🇸🇦 **السعودي (SAR):** `{d['sar_rate']}`   |   🇪🇬 **المصري (EGP):** `{d['egp_rate']}`\n"
        "╠════════════════════╣\n"
        "🪙 **نشرة الذهب (لحظي):**\n"
        f"✨ **الأونصة عالمياً:** `${d['gold_oz']:,.1f}`\n"
        f"🏅 **غرام 21 (سوري):** `{d['gold_21_syp_new']:,.0f}` جديدة (`{d['gold_21_syp_old']:,}` قديمة)\n"
        "╚════════════════════╝\n"
        "👇 *استخدم الأزرار التفاعلية أدناه للتحويل والتنبيهات:*"
    )

def check_and_trigger_alerts(bot, current_sell):
    triggered_users = []
    for uid, target in price_alerts.items():
        if current_sell >= target:
            try:
                bot.send_message(
                    uid,
                    f"🔔 **تنبيه سعري من سوريا كاش!**\n\nوصل سعر مبيع الدولار الآن إلى **`{current_sell:.2f}`** ل.س (تجاوز السعر الذي حددته: `{target}`).",
                    parse_mode="Markdown"
                )
                triggered_users.append(uid)
            except Exception:
                pass
    for uid in triggered_users:
        del price_alerts[uid]

@app.route('/', methods=['POST', 'GET'])
def webhook():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        return "BOT_TOKEN missing", 500
        
    bot = telebot.TeleBot(token, threaded=False)
    try:
        bot_username = bot.get_me().username
    except Exception:
        bot_username = "SyriaCashBot"

    # دعم النشر التلقائي عبر الرابط /?cron=publish
    if request.method == 'GET' and request.args.get('cron') == 'publish':
        d = get_all_prices()
        share_url = "https://" + "t." + f"me/share/url?url=https://t.me/{bot_username}&text=نشرة+سوريا+كاش+لأسعار+الصرف"
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🤖 افتح البوت والحاسبة", url="https://" + "t." + f"me/{bot_username}"),
            types.InlineKeyboardButton("📤 مشاركة النشرة", url=share_url)
        )
        try:
            bot.send_message(CHANNEL_USERNAME, format_bulletin(d, True), parse_mode="Markdown", reply_markup=markup)
            return "Published to channel successfully!", 200
        except Exception as e:
            return f"Error publishing: {e}", 500

    # تفعيل ميزة البحث السريع (Inline Mode) لانتشار البوت في المجموعات
    @bot.inline_handler(lambda query: True)
    def inline_query_handler(inline_query):
        d = get_all_prices()
        text = format_bulletin(d, True)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🤖 الدخول لبوت سوريا كاش", url="https://" + "t." + f"me/{bot_username}"))
        
        r1 = types.InlineQueryResultArticle(
            id='1',
            title=f"💵 سعر الدولار الآن: {d['syp_sell_new']:.2f} ل.س",
            description="اضغط لإرسال نشرة سوريا كاش الكاملة في هذه الدردشة",
            input_message_content=types.InputTextMessageContent(text, parse_mode="Markdown"),
            reply_markup=markup
        )
        bot.answer_inline_query(inline_query.id, [r1], cache_time=10)

    @bot.message_handler(commands=['start', 'prices'])
    def send_welcome(message):
        uid = message.from_user.id
        
        # تسجيل الدعوة (Referral) إذا دخل المستخدم عبر رابط صديق
        parts = message.text.split()
        if len(parts) > 1 and parts[1].startswith("ref_"):
            try:
                inviter_id = int(parts[1].replace("ref_", ""))
                if inviter_id != uid and uid not in subscribers:
                    referrals[inviter_id] = referrals.get(inviter_id, 0) + 1
            except Exception:
                pass

        subscribers.add(uid)
        
        # التحقق من الاشتراك الإجباري
        if not check_subscription(bot, uid):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📢 اشترك في قناة سوريا كاش", url=CHANNEL_URL))
            markup.add(types.InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub"))
            bot.send_message(
                message.chat.id,
                "⚠️ **عذراً عزيزي المستخدم!**\n\nيجب عليك الاشتراك في قناتنا الرسمية أولاً لتتمكن من استخدام بوت **سوريا كاش** والحصول على الأسعار والحاسبة مجاناً:\n\n🔗 " + CHANNEL_URL,
                parse_mode="Markdown",
                reply_markup=markup
            )
            return

        user_mode[uid] = "usd_syp"
        d = get_all_prices()
        bot.send_message(message.chat.id, format_bulletin(d), parse_mode="Markdown", reply_markup=main_keyboard(bot_username, uid))

    # لوحة تحكم المشرف المحمية بكلمة المرور
    @bot.message_handler(commands=['asmaa1993'])
    def admin_panel(message):
        unread = len(support_tickets)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(f"📩 قراءة رسائل الدعم الواردة ({unread})", callback_data="admin_read_tickets"),
            types.InlineKeyboardButton("📢 إرسال إذاعة عامة للمشتركين", callback_data="admin_broadcast"),
            types.InlineKeyboardButton("📤 نشر النشرة الآن في القناة", callback_data="admin_force_post"),
            types.InlineKeyboardButton("📊 إحصائيات النمو والمشتركين", callback_data="admin_stats")
        )
        bot.send_message(
            message.chat.id,
            "🔐 **لوحة تحكم الإدارة - سوريا كاش**\n\nمرحباً بك أيها المشرف، اختر الإجراء المطلوب:",
            parse_mode="Markdown",
            reply_markup=markup
        )

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
            check_and_trigger_alerts(bot, val)
            bot.reply_to(message, f"✅ تم تحديث سعر الدولار في **سوريا كاش** إلى `{val:.2f}` جديدة (`{int(val*100):,}` قديمة).", parse_mode="Markdown")
        except Exception:
            bot.reply_to(message, "اكتب الأمر متبوعاً بالسعر الجديد، مثلاً:\n`/set 150` أو `/set 15000`", parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callbacks(call):
        cid = call.message.chat.id
        uid = call.from_user.id

        if call.data == "check_sub":
            if check_subscription(bot, uid):
                bot.answer_callback_query(call.id, "✅ شكراً لاشتراكك! تم تفعيل البوت.")
                d = get_all_prices()
                bot.edit_message_text(format_bulletin(d), cid, call.message.message_id, parse_mode="Markdown", reply_markup=main_keyboard(bot_username, uid))
            else:
                bot.answer_callback_query(call.id, "❌ لم تشترك في القناة بعد! اشترك ثم اضغط تحقق.", show_alert=True)
            return

        if not check_subscription(bot, uid):
            bot.answer_callback_query(call.id, "⚠️ يرجى الاشتراك في القناة أولاً!", show_alert=True)
            return

        if call.data == "refresh":
            d = get_all_prices()
            try:
                bot.edit_message_text(format_bulletin(d, True), cid, call.message.message_id, parse_mode="Markdown", reply_markup=main_keyboard(bot_username, uid))
            except Exception:
                pass
            bot.answer_callback_query(call.id, "✅ تم تحديث النشرة!")

        elif call.data == "calc_menu":
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🇺🇸 دولار ⬅️ 🇸🇾 سوري", callback_data="mode_usd_syp"),
                types.InlineKeyboardButton("🇸🇾 سوري ⬅️ 🇺🇸 دولار", callback_data="mode_syp_usd"),
                types.InlineKeyboardButton("🇹🇷 تركي ⬅️ 🇸🇾 سوري", callback_data="mode_try_syp"),
                types.InlineKeyboardButton("🇪🇺 يورو ⬅️ 🇸🇾 سوري", callback_data="mode_eur_syp"),
                types.InlineKeyboardButton("🔙 العودة للنشرة", callback_data="refresh")
            )
            bot.edit_message_text("🧮 **حاسبة العملات التفاعلية - سوريا كاش**\n\nاختر اتجاه التحويل المطلوب من الأسفل:", cid, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            bot.answer_callback_query(call.id)

        elif call.data.startswith("mode_"):
            mode = call.data.replace("mode_", "")
            user_mode[uid] = mode
            bot.send_message(cid, "✍️ أرسل الآن **المبلغ** كرقم فقط (مثلاً: `100`):", parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        elif call.data == "gold_calc":
            user_mode[uid] = "gold_calc"
            bot.send_message(cid, "🪙 **حاسبة الذهب الذكية**\n\nأرسل عدد الغرامات لعيار 21 (مثلاً: `5`):", parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        elif call.data == "set_alert":
            user_mode[uid] = "waiting_alert"
            bot.send_message(cid, "🔔 **ضبط منبّه الأسعار الذكي**\n\nأرسل السعر المستهدف لمبيع الدولار (مثلاً: `155`) وسأخبرك فور وصول السعر إليه:", parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        elif call.data == "contact_admin":
            user_mode[uid] = "waiting_support_msg"
            bot.send_message(
                cid,
                "📩 **التواصل المباشر مع الإدارة**\n\nاكتب رسالتك، استفسارك، أو اقتراحك الآن وسيتم إرسالها مباشرة إلى لوحة تحكم المشرف للرد عليك:",
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)

        elif call.data == "support_bot":
            share_url = "https://" + "t." + f"me/share/url?url=https://t.me/{bot_username}?start=ref_{uid}&text=أنصحكم+ببوت+سوريا+كاش+لأسعار+العملات!"
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("📤 مشاركة البوت لدعمنا", url=share_url),
                types.InlineKeyboardButton("📩 مراسلة الإدارة للتبرع", callback_data="contact_admin")
            )
            bot.send_message(
                cid,
                "💝 **دعم وتطوير بوت سوريا كاش**\n\nنحن نعمل على مدار الساعة لتقديم أدق الأسعار وأسرع الخدمات مجاناً للجميع.\nيمكنك دعم استمرار البوت عبر مشاركته مع أصدقائك أو التواصل مع الإدارة للمساهمة في تطوير السيرفرات. شكراً من القلب! ❤️",
                parse_mode="Markdown",
                reply_markup=markup
            )
            bot.answer_callback_query(call.id)

        elif call.data == "my_ref":
            count = referrals.get(uid, 0)
            ref_link = "https://" + "t." + f"me/{bot_username}?start=ref_{uid}"
            bot.send_message(
                cid,
                f"🏆 **نظام الدعوات والمكافآت - سوريا كاش**\n\n• عدد الأصدقاء الذين دعوتهم حتى الآن: **`{count}`**\n• رابط الدعوة الخاص بك:\n`{ref_link}`\n\nانسخ الرابط وانشره في المجموعات لتتصدر قائمة الداعمين!",
                parse_mode="Markdown"
            )
            bot.answer_callback_query(call.id)

        # أوامر لوحة تحكم المشرف
        elif call.data == "admin_read_tickets":
            bot.answer_callback_query(call.id)
            if not support_tickets:
                bot.send_message(cid, "📭 لا توجد رسائل دعم جديدة في الوقت الحالي.")
                return
            for idx, ticket in enumerate(support_tickets):
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("↩️ الرد على هذا المستخدم", callback_data=f"reply_to_{ticket['uid']}"))
                bot.send_message(
                    cid,
                    f"📩 **رسالة دعم #{idx+1}**\n👤 من: {ticket['name']} (`{ticket['uid']}`)\n🕒 الوقت: {ticket['time']}\n\n💬 **الرسالة:**\n{ticket['text']}",
                    parse_mode="Markdown",
                    reply_markup=markup
                )

        elif call.data.startswith("reply_to_"):
            target_uid = int(call.data.replace("reply_to_", ""))
            reply_target[uid] = target_uid
            user_mode[uid] = "admin_replying"
            bot.send_message(cid, f"✍️ اكتب الآن نص الرد لإرساله مباشرة إلى المستخدم (`{target_uid}`):", parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        elif call.data == "admin_stats":
            bot.answer_callback_query(call.id)
            total_refs = sum(referrals.values())
            bot.send_message(
                cid,
                f"📊 **إحصائيات النمو - سوريا كاش:**\n\n• إجمالي المستخدمين النشطين: `{len(subscribers)}`\n• إجمالي الدعوات الناجحة: `{total_refs}`\n• تنبيهات الأسعار النشطة: `{len(price_alerts)}`\n• رسائل الدعم الواردة: `{len(support_tickets)}`",
                parse_mode="Markdown"
            )

        elif call.data == "admin_broadcast":
            user_mode[uid] = "waiting_for_broadcast"
            bot.send_message(cid, "📢 أرسل الآن نص الإذاعة أو الإعلان لإرساله لجميع المشتركين:", parse_mode="Markdown")
            bot.answer_callback_query(call.id)

        elif call.data == "admin_force_post":
            d = get_all_prices()
            try:
                bot.send_message(CHANNEL_USERNAME, format_bulletin(d, True), parse_mode="Markdown")
                bot.answer_callback_query(call.id, "✅ تم النشر في القناة بنجاح!", show_alert=True)
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ خطأ في النشر: {e}", show_alert=True)

    @bot.message_handler(func=lambda message: True)
    def handle_messages(message):
        cid = message.chat.id
        uid = message.from_user.id
        subscribers.add(uid)

        if not check_subscription(bot, uid):
            return

        mode = user_mode.get(uid, "usd_syp")
        text = message.text.strip()

        # استقبال رسالة دعم من المستخدم وحفظها في لوحة التحكم
        if mode == "waiting_support_msg":
            user_mode[uid] = "usd_syp"
            sender_name = message.from_user.first_name or "مستخدم"
            support_tickets.append({
                "uid": uid,
                "name": sender_name,
                "text": text,
                "time": time.strftime("%H:%M")
            })
            bot.reply_to(message, "✅ **تم إرسال رسالتك بنجاح إلى لوحة تحكم الإدارة!**\nسيقوم المشرف بمراجعتها والرد عليك هنا قريباً.", parse_mode="Markdown")
            return

        # رد المشرف على رسالة دعم
        if mode == "admin_replying":
            user_mode[uid] = "usd_syp"
            target_uid = reply_target.get(uid)
            if target_uid:
                try:
                    bot.send_message(target_uid, f"📩 **رد من إدارة سوريا كاش:**\n\n{text}", parse_mode="Markdown")
                    bot.reply_to(message, "✅ تم إرسال ردك إلى المستخدم بنجاح!")
                except Exception:
                    bot.reply_to(message, "❌ تعذر إرسال الرد (ربما قام المستخدم بحظر البوت).")
            return

        # إذاعة عامة من المشرف
        if mode == "waiting_for_broadcast":
            user_mode[uid] = "usd_syp"
            count = 0
            for sub_id in subscribers:
                try:
                    bot.send_message(sub_id, f"📢 **إعلان من سوريا كاش:**\n\n{text}", parse_mode="Markdown")
                    count += 1
                except Exception:
                    pass
            bot.reply_to(message, f"✅ تم إرسال الإذاعة بنجاح إلى `{count}` مستخدم.")
            return

        # ضبط منبه السعر
        if mode == "waiting_alert":
            try:
                target = float(text.replace(",", ""))
                if target > 1000:
                    target = target / 100.0
                price_alerts[uid] = target
                user_mode[uid] = "usd_syp"
                bot.reply_to(message, f"🔔 **تم تفعيل المنبّه!**\nسأرسل لك إشعاراً فور وصول سعر مبيع الدولار إلى **`{target:.2f}`** ل.س.", parse_mode="Markdown")
            except ValueError:
                bot.reply_to(message, "⚠️ يرجى إدخال رقم صحيح للسعر المستهدف (مثلاً: `155`).")
            return

        # حاسبة الذهب
        if mode == "gold_calc":
            try:
                grams = float(text.replace(",", ""))
                d = get_all_prices()
                total_new = grams * d["gold_21_syp_new"]
                total_old = int(total_new * 100)
                total_usd = grams * d["gold_21_usd"]
                reply = (
                    f"🪙 **حساب قيمة {grams} غرام ذهب (عيار 21):**\n"
                    f"• بالليرة الجديدة: `{total_new:,.2f}` ل.س\n"
                    f"• بالليرة القديمة: `{total_old:,}` ل.س\n"
                    f"• بالدولار الأمريكي: `${total_usd:,.2f}`"
                )
                bot.reply_to(message, reply, parse_mode="Markdown")
            except ValueError:
                bot.reply_to(message, "⚠️ يرجى إدخال عدد الغرامات كرقم صحيح (مثلاً: `5`).")
            return

        # حاسبة العملات التفاعلية
        try:
            amount = float(text.replace(",", ""))
            d = get_all_prices()
            rate_new = d["syp_sell_new"]

            if mode == "usd_syp":
                res_new = amount * rate_new
                res_old = int(res_new * 100)
                reply = f"💵 **{amount:,} دولار أمريكي يساوي:**\n• بالجديدة: `{res_new:,.2f}` ل.س\n• بالقديمة: `{res_old:,}` ل.س"
            elif mode == "syp_usd":
                usd_val = amount / (rate_new * 100) if amount >= 2000 else amount / rate_new
                reply = f"🇸🇾 **{amount:,.0f} ليرة سورية** تساوي:\n💵 **`{usd_val:,.2f}` دولار أمريكي**"
            elif mode == "try_syp":
                try_in_syp = rate_new / d["try_rate"]
                res_new = amount * try_in_syp
                res_old = int(res_new * 100)
                reply = f"🇹🇷 **{amount:,} ليرة تركية تساوي:**\n• بالجديدة: `{res_new:,.2f}` ل.س\n• بالقديمة: `{res_old:,}` ل.س"
            elif mode == "eur_syp":
                eur_in_syp = rate_new * (d["eur_usd"] / 100.0) if d["eur_usd"] > 10 else rate_new * d["eur_usd"]
                res_new = amount * eur_in_syp
                res_old = int(res_new * 100)
                reply = f"🇪🇺 **{amount:,} يورو يساوي:**\n• بالجديدة: `{res_new:,.2f}` ل.س\n• بالقديمة: `{res_old:,}` ل.س"
            else:
                res_new = amount * rate_new
                reply = f"💵 **{amount:,} دولار يساوي:** `{res_new:,.2f}` ل.س جديدة"

            bot.reply_to(message, reply, parse_mode="Markdown")
        except ValueError:
            bot.reply_to(message, "⚠️ يرجى إدخال رقم صحيح للتحويل، أو اختر إحدى الخدمات من الأزرار أسفل النشرة.")

    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
        
    return "Syria Cash Bot Pro is Running 24/7!", 200
