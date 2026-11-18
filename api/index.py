import os
import time
import requests
from flask import Flask, request
import telebot
from telebot import types

app = Flask(__name__)

user_mode = {}
custom_syp = {"buy": 149.50, "sell": 150.00, "official": 122.50}
support_tickets = []  
subscribers = set()   
price_alerts = {}     
reply_target = {}     

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

    oz_buy = data["gold_oz"]
    oz_sell = oz_buy + 5.0
    g24_buy = oz_buy / 31.1035
    g24_sell = oz_sell / 31.1035
    g21_buy = g24_buy * 0.875
    g21_sell = g24_sell * 0.875
    g18_buy = g24_buy * 0.750
    g18_sell = g24_sell * 0.750

    data["gold"] = {
        "oz_buy": round(oz_buy, 1), "oz_sell": round(oz_sell, 1),
        "g24_buy": round(g24_buy, 2), "g24_sell": round(g24_sell, 2),
        "g21_buy": round(g21_buy, 2), "g21_sell": round(g21_sell, 2),
        "g18_buy": round(g18_buy, 2), "g18_sell": round(g18_sell, 2),
    }

    gold_21_syp_new = round(g21_sell * data["syp_sell_new"], 2)
    data["gold_21_syp_new"] = gold_21_syp_new
    data["gold_21_syp_old"] = int(gold_21_syp_new * 100)

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
    share_url = "https://" + "t." + f"me/share/url?url=https://t.me/{bot_username}&text=أفضل+منصة+لأسعار+الصرف+والذهب+في+سوريا+-+سوريا+كاش"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 تحديث النشرة الآن", callback_data="refresh"),
        types.InlineKeyboardButton("🧮 حاسبة العملات التفاعلية", callback_data="calc_menu"),
        types.InlineKeyboardButton("🪙 أسعار وحاسبة الذهب", callback_data="gold_menu"),
        types.InlineKeyboardButton("🔔 ضبط منبّه الأسعار", callback_data="set_alert"),
        types.InlineKeyboardButton("📩 التواصل مع الإدارة والدعم", callback_data="contact_admin"),
        types.InlineKeyboardButton("💝 دعم وتطوير البوت", callback_data="support_bot"),
        types.InlineKeyboardButton("📢 قناة التليجرام الرسمية", url=CHANNEL_URL),
        types.InlineKeyboardButton("📤 مشاركة البوت مع الأصدقاء", url=share_url)
    )
    return markup

def back_home_keyboard():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏠 القائمة الرئيسية والعودة", callback_data="refresh"))
    return markup

def format_bulletin(d, updated=False):
    header = "🌟 **منصة سوريا كاش الاقتصادية** 🌟"
    sub = "📊 *(نشرة محدثة للأسعار اللحظية في السوق السوري)*" if updated else "📊 *(النشرة الرسمية لأسعار العملات والذهب)*"
    buy_old = int(d["syp_buy_new"] * 100)
    sell_old = int(d["syp_sell_new"] * 100)
    g = d["gold"]
    
    return (
        f"{header}\n"
        f"{sub}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🇺🇸 **سعر الدولار الأمريكي (السوق المتداول):**\n"
        f"  ▪️ **مبيع:** ` {d['syp_sell_new']:.2f} ` ل.س  *( `{sell_old:,}` قديمة )*\n"
        f"  ▪️ **شراء:** ` {d['syp_buy_new']:.2f} ` ل.س  *( `{buy_old:,}` قديمة )*\n"
        f"  🟢 *حالة السوق: مباشر ({d['time_str']}) | {d['change_pct']} 📈*\n\n"
        "🏛 **سعر الدولار الرسمي (مصرف سوريا المركزي):**\n"
        f"  ▪️ **السعر المعتمد:** ` {d['syp_official_new']:.2f} ` ل.س\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🌍 **أسعار العملات العربية والأجنبية:**\n"
        f"  🇪🇺 اليورو (EUR): `{d['eur_usd']}`   |   🇹🇷 التركي (TRY): `{d['try_rate']}`\n"
        f"  🇸🇦 السعودي (SAR): `{d['sar_rate']}`   |   🇪🇬 المصري (EGP): `{d['egp_rate']}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🪙 **أسعار الذهب العالمية (بالدولار الأمريكي فقط):**\n"
        f"  🔸 **أونصة الذهب:** مبيع `$ {g['oz_sell']:,}` | شراء `$ {g['oz_buy']:,}`\n"
        f"  🔸 **غرام 24:** مبيع `$ {g['g24_sell']}` | شراء `$ {g['g24_buy']}`\n"
        f"  🔸 **غرام 21:** مبيع `$ {g['g21_sell']}` | شراء `$ {g['g21_buy']}`\n"
        f"  🔸 **غرام 18:** مبيع `$ {g['g18_sell']}` | شراء `$ {g['g18_buy']}`\n"
        f"  📍 *غرام 21 (بالليرة السورية):* ` {d['gold_21_syp_new']:,.0f} ` ل.س\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *اختر من الأزرار أدناه للبدء فوراً:*"
    )

def check_and_trigger_alerts(bot, current_sell):
    triggered_users = []
    for uid, target in price_alerts.items():
        if current_sell >= target:
            try:
                bot.send_message(
                    uid,
                    f"🚨 **تنبيه هام من سوريا كاش!**\n\nلقد وصل سعر مبيع الدولار الآن في السوق إلى **`{current_sell:.2f}`** ل.س، وهو السعر المستهدف الذي طالبت بتنبيهك عند وصوله (`{target}`).",
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

    if request.method == 'GET' and request.args.get('cron') == 'publish':
        d = get_all_prices()
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🤖 افتح بوت سوريا كاش للحاسبة والخدمات", url="https://" + "t." + f"me/{bot_username}"))
        try:
            bot.send_message(CHANNEL_USERNAME, format_bulletin(d, True), parse_mode="Markdown", reply_markup=markup)
            return "Published to channel successfully!", 200
        except Exception as e:
            return f"Error publishing: {e}", 500

    @bot.inline_handler(lambda query: True)
    def inline_query_handler(inline_query):
        d = get_all_prices()
        text = format_bulletin(d, True)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🤖 افتح بوت سوريا كاش", url="https://" + "t." + f"me/{bot_username}"))
        
        r1 = types.InlineQueryResultArticle(
            id='1',
            title=f"💵 سعر الدولار الآن: {d['syp_sell_new']:.2f} ل.س",
            description="انقر لإرسال النشرة الاقتصادية الكاملة في هذه الدردشة",
            input_message_content=types.InputTextMessageContent(text, parse_mode="Markdown"),
            reply_markup=markup
        )
        bot.answer_inline_query(inline_query.id, [r1], cache_time=10)

    @bot.message_handler(commands=['start', 'prices'])
    def send_welcome(message):
        uid = message.from_user.id
        subscribers.add(uid)
        
        if not check_subscription(bot, uid):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📢 الانضمام لقناة سوريا كاش", url=CHANNEL_URL))
            markup.add(types.InlineKeyboardButton("✅ لقد اشتركت، تحقق الآن", callback_data="check_sub"))
            bot.send_message(
                message.chat.id,
                "⚠️ **عذراً، اشترك في القناة أولاً لتستمتع بخدمات البوت:**\n\nنرحّب بك في **سوريا كاش**، يرجى الانضمام للقناة الرسمية لتفعيل حسابك:\n\n🔗 " + CHANNEL_URL,
                parse_mode="Markdown",
                reply_markup=markup
            )
            return

        user_mode[uid] = "usd_syp"
        d = get_all_prices()
        bot.send_message(message.chat.id, format_bulletin(d), parse_mode="Markdown", reply_markup=main_keyboard(bot_username))

    @bot.message_handler(commands=['asmaa1993'])
    def admin_panel(message):
        unread = len(support_tickets)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(f"📩 قراءة رسائل الدعم الواردة ({unread})", callback_data="admin_read_tickets"),
            types.InlineKeyboardButton("📢 إرسال اذاعة عامة للمستخدمين", callback_data="admin_broadcast"),
            types.InlineKeyboardButton("📤 نشر النشرة الفورية في القناة", callback_data="admin_force_post"),
            types.InlineKeyboardButton("📊 إحصائيات المشتركين والنشاط", callback_data="admin_stats"),
            types.InlineKeyboardButton("🏠 العودة للقائمة الرئيسية", callback_data="refresh")
        )
        bot.send_message(
            message.chat.id,
            "🔐 **لوحة تحكم المشرف الرئيسية - سوريا كاش**\n\nأهلاً بك، يرجى اختيار العملية المطلوبة:",
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
            bot.reply_to(message, f"✅ تم تحديث سعر صرف الدولار بنجاح إلى `{val:.2f}` جديدة (`{int(val*100):,}` قديمة).", parse_mode="Markdown", reply_markup=back_home_keyboard())
        except Exception:
            bot.reply_to(message, "⚠️ صيغة الأمر غير صحيحة. اكتب الأمر متبوعاً بالسعر الجديد، مثلاً:\n`/set 150` أو `/set 15000`", parse_mode="Markdown", reply_markup=back_home_keyboard())

    @bot.callback_query_handler(func=lambda call: True)
    def handle_callbacks(call):
        cid = call.message.chat.id
        uid = call.from_user.id

        if call.data == "check_sub":
            if check_subscription(bot, uid):
                bot.answer_callback_query(call.id, "✅ تم التحقق من اشتراكك بنجاح! أهلاً بك.")
                d = get_all_prices()
                bot.edit_message_text(format_bulletin(d), cid, call.message.message_id, parse_mode="Markdown", reply_markup=main_keyboard(bot_username))
            else:
                bot.answer_callback_query(call.id, "❌ لم تقم بالاشتراك في القناة بعد! يرجى الاشتراك أولاً.", show_alert=True)
            return

        if not check_subscription(bot, uid):
            bot.answer_callback_query(call.id, "⚠️ يجب الاشتراك في القناة المخصصة أولاً!", show_alert=True)
            return

        if call.data == "refresh":
            user_mode[uid] = "usd_syp"
            d = get_all_prices()
            try:
                bot.edit_message_text(format_bulletin(d, True), cid, call.message.message_id, parse_mode="Markdown", reply_markup=main_keyboard(bot_username))
            except Exception:
                bot.send_message(cid, format_bulletin(d, True), parse_mode="Markdown", reply_markup=main_keyboard(bot_username))
            bot.answer_callback_query(call.id, "✅ تم تحديث النشرة بنجاح")

        elif call.data == "calc_menu":
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🇺🇸 دولار ⬅️ 🇸🇾 ليرة سورية", callback_data="mode_usd_syp"),
                types.InlineKeyboardButton("🇸🇾 ليرة سورية ⬅️ 🇺🇸 دولار", callback_data="mode_syp_usd"),
                types.InlineKeyboardButton("🇹🇷 ليرة تركية ⬅️ 🇸🇾 سوري", callback_data="mode_try_syp"),
                types.InlineKeyboardButton("🇪🇺 يورو ⬅️ 🇸🇾 ليرة سورية", callback_data="mode_eur_syp"),
                types.InlineKeyboardButton("🏠 العودة للقائمة الرئيسية", callback_data="refresh")
            )
            bot.edit_message_text("🧮 **حاسبة العملات الذكية والتفاعلية**\n\nاختر اتجاه التحويل المفضل لديك من الأزرار أدناه:", cid, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            bot.answer_callback_query(call.id)

        elif call.data.startswith("mode_"):
            mode = call.data.replace("mode_", "")
            user_mode[uid] = mode
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❌ إلغاء وعودة للقائمة", callback_data="refresh"))
            bot.send_message(cid, "✍️ أرسل الآن **المبلغ المراد تحويله** كرقم فقط (مثلاً: `100` أو `5000`):", parse_mode="Markdown", reply_markup=markup)
            bot.answer_callback_query(call.id)

        elif call.data == "gold_menu":
            d = get_all_prices()
            g = d["gold"]
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("⚖️ حاسبة وزن وسعر الذهب", callback_data="gold_calc_start"),
                types.InlineKeyboardButton("🏠 العودة للقائمة الرئيسية", callback_data="refresh")
            )
            gold_info = (
                "🪙 **المرجع الشامل لأسعار الذهب (بالدولار الأمريكي)**\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"• **أونصة الذهب:** مبيع `$ {g['oz_sell']:,}` | شراء `$ {g['oz_buy']:,}`\n"
                f"• **غرام عيار 24:** مبيع `$ {g['g24_sell']}` | شراء `$ {g['g24_buy']}`\n"
                f"• **غرام عيار 21:** مبيع `$ {g['g21_sell']}` | شراء `$ {g['g21_buy']}`\n"
                f"• **غرام عيار 18:** مبيع `$ {g['g18_sell']}` | شراء `$ {g['g18_buy']}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "👇 *اضغط على زر الحاسبة أدناه لحساب غراماتك المحددة بالليرة والدولار:*"
            )
            bot.edit_message_text(gold_info, cid, call.message.message_id, parse_mode="Markdown", reply_markup=markup)
            bot.answer_callback_query(call.id)

        elif call.data == "gold_calc_start":
            user_mode[uid] = "gold_calc"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❌ إلغاء وعودة للقائمة", callback_data="refresh"))
            bot.send_message(cid, "🪙 **حاسبة وزن الذهب الذكية**\n\nأرسل الآن عدد غرامات الذهب المطلوبة لعيار 21 (مثلاً: `5` أو `10`):", parse_mode="Markdown", reply_markup=markup)
            bot.answer_callback_query(call.id)

        elif call.data == "set_alert":
            user_mode[uid] = "waiting_alert"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❌ إلغاء وعودة للقائمة", callback_data="refresh"))
            bot.send_message(cid, "🔔 **خدمة منبّه الأسعار الآلي**\n\nأرسل السعر المستهدف لمبيع الدولار الذي ترغب بمراقبته (مثلاً: `155` أو `160`) وسنقوم بتنبيهك فور وصول السوق إليه:", parse_mode="Markdown", reply_markup=markup)
            bot.answer_callback_query(call.id)

        elif call.data == "contact_admin":
            user_mode[uid] = "waiting_support_msg"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❌ إلغاء وعودة للقائمة", callback_data="refresh"))
            bot.send_message(
                cid,
                "📩 **التواصل المباشر مع طاقم الإدارة والدعم**\n\nاكتب رسالتك، استفسارك، أو اقتراحك الآن بكل أريحية، وسيتم تحويلها إلى لوحة تحكم المشرف للرد الفوري عليك:",
                parse_mode="Markdown",
                reply_markup=markup
            )
            bot.answer_callback_query(call.id)

        elif call.data == "support_bot":
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(
                types.InlineKeyboardButton("📩 مراسلة الإدارة للمساهمة", callback_data="contact_admin"),
                types.InlineKeyboardButton("🏠 العودة للقائمة الرئيسية", callback_data="refresh")
            )
            bot.send_message(
                cid,
                "💝 **الدعم والمساهمة في استمرار سوريا كاش**\n\nنحن نسعى لتقديم أسعار دقيقة وخدمات برمجية مجانية متكاملة على مدار الساعة.\nيمكنك دعم المشروع عبر التوصية بالبوت لأصدقائك أو التواصل مع المشرف للمساهمة في تطوير البنية التحتية. شكراً لثقتكم الغالية! ❤️",
                parse_mode="Markdown",
                reply_markup=markup
            )
            bot.answer_callback_query(call.id)

        elif call.data == "admin_read_tickets":
            bot.answer_callback_query(call.id)
            if not support_tickets:
                bot.send_message(cid, "📭 لا توجد أي رسائل دعم جديدة معلقة في الوقت الحالي.", reply_markup=back_home_keyboard())
                return
            for idx, ticket in enumerate(support_tickets):
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("↩️ الرد على هذا المستخدم", callback_data=f"reply_to_{ticket['uid']}"),
                    types.InlineKeyboardButton("🗑 حذف الرسالة", callback_data=f"del_ticket_{idx}")
                )
                bot.send_message(
                    cid,
                    f"📩 **رسالة دعم رقم ({idx+1})**\n👤 المُرسل: {ticket['name']} (`{ticket['uid']}`)\n🕒 التوقيت: {ticket['time']}\n\n💬 **محتوى الرسالة:**\n{ticket['text']}",
                    parse_mode="Markdown",
                    reply_markup=markup
                )

        elif call.data.startswith("reply_to_"):
            target_uid = int(call.data.replace("reply_to_", ""))
            reply_target[uid] = target_uid
            user_mode[uid] = "admin_replying"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="refresh"))
            bot.send_message(cid, f"✍️ اكتب الآن نص الرد الرسمي لإرساله فوراً للمستخدم (`{target_uid}`):", parse_mode="Markdown", reply_markup=markup)
            bot.answer_callback_query(call.id)

        elif call.data == "admin_stats":
            bot.answer_callback_query(call.id)
            bot.send_message(
                cid,
                f"📊 **إحصائيات التشغيل والنشاط - سوريا كاش:**\n\n• إجمالي المستخدمين المسجلين: `{len(subscribers)}`\n• تنبيهات الأسعار الفعالة: `{len(price_alerts)}`\n• رسائل الدعم الواردة غير المنتهية: `{len(support_tickets)}`",
                parse_mode="Markdown",
                reply_markup=back_home_keyboard()
            )

        elif call.data == "admin_broadcast":
            user_mode[uid] = "waiting_for_broadcast"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="refresh"))
            bot.send_message(cid, "📢 أرسل الآن نص الإعلان أو الإذاعة البرمجية الذي تريد بثه لجميع المشتركين:", parse_mode="Markdown", reply_markup=markup)
            bot.answer_callback_query(call.id)

        elif call.data == "admin_force_post":
            d = get_all_prices()
            try:
                bot.send_message(CHANNEL_USERNAME, format_bulletin(d, True), parse_mode="Markdown")
                bot.answer_callback_query(call.id, "✅ تم نشر النشرة الفورية في القناة بنجاح!", show_alert=True)
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ حدث خطأ أثناء النشر: {e}", show_alert=True)

    @bot.message_handler(func=lambda message: True)
    def handle_messages(message):
        cid = message.chat.id
        uid = message.from_user.id
        subscribers.add(uid)

        if not check_subscription(bot, uid):
            return

        mode = user_mode.get(uid, "usd_syp")
        text = message.text.strip()

        if mode == "waiting_support_msg":
            user_mode[uid] = "usd_syp"
            sender_name = message.from_user.first_name or "مستخدم كريم"
            support_tickets.append({
                "uid": uid,
                "name": sender_name,
                "text": text,
                "time": time.strftime("%H:%M")
            })
            d = get_all_prices()
            bot.send_message(
                cid,
                "✅ **تم استلام رسالتك وإرسالها للإدارة بنجاح!**\nشكراً لتواصلك معنا، سنقوم بمراجعتها والرد عليك قريباً.\n\n*(تم إرجاعك للقائمة الرئيسية تلقائياً)*",
                parse_mode="Markdown"
            )
            bot.send_message(cid, format_bulletin(d), parse_mode="Markdown", reply_markup=main_keyboard(bot_username))
            return

        if mode == "admin_replying":
            user_mode[uid] = "usd_syp"
            target_uid = reply_target.get(uid)
            if target_uid:
                try:
                    bot.send_message(target_uid, f"📩 **إشعار رد رسمي من إدارة سوريا كاش:**\n\n{text}", parse_mode="Markdown")
                    bot.reply_to(message, "✅ تم إرسال الرد بنجاح للمستخدم!", reply_markup=back_home_keyboard())
                except Exception:
                    bot.reply_to(message, "❌ تعذر إرسال الرد (ربما قام المستخدم بحظر البوت أو توقفه).", reply_markup=back_home_keyboard())
            return

        if mode == "waiting_for_broadcast":
            user_mode[uid] = "usd_syp"
            count = 0
            for sub_id in subscribers:
                try:
                    bot.send_message(sub_id, f"📢 **إعلان هام من إدارة سوريا كاش:**\n\n{text}", parse_mode="Markdown")
                    count += 1
                except Exception:
                    pass
            bot.reply_to(message, f"✅ تم إرسال الإذاعة بنجاح إلى إجمالي `{count}` مستخدم نشط.", reply_markup=back_home_keyboard())
            return

        if mode == "waiting_alert":
            try:
                target = float(text.replace(",", ""))
                if target > 1000:
                    target = target / 100.0
                price_alerts[uid] = target
                user_mode[uid] = "usd_syp"
                d = get_all_prices()
                bot.send_message(
                    cid,
                    f"🔔 **تم تفعيل منبّه الأسعار بنجاح!**\nسنجري مراقبة مستمرة، وسنرسل لك إشعاراً فورياً فور وصول مبيع الدولار إلى السعر المستهدف: **`{target:.2f}`** ل.س.\n\n*(تم العودة للقائمة الرئيسية تلقائياً)*",
                    parse_mode="Markdown"
                )
                bot.send_message(cid, format_bulletin(d), parse_mode="Markdown", reply_markup=main_keyboard(bot_username))
            except ValueError:
                bot.reply_to(message, "⚠️ يرجى إدخال رقم صحيح وواضح للسعر (مثلاً: `155` أو `155.5`).")
            return

        if mode == "gold_calc":
            try:
                grams = float(text.replace(",", ""))
                d = get_all_prices()
                g = d["gold"]
                total_usd = grams * g['g21_sell']
                total_new = grams * d["gold_21_syp_new"]
                total_old = int(total_new * 100)
                
                reply = (
                    f"🪙 **نتيجة حساب وزن الذهب ({grams} غرام - عيار 21):**\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"• **القيمة الإجمالية بالدولار:** `$ {total_usd:,.2f}`\n"
                    f"• **القيمة بالليرة الجديدة:** ` {total_new:,.2f} ` ل.س\n"
                    f"• **القيمة بالليرة القديمة:** ` {total_old:,} ` ل.س\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    "*(تم إرجاعك للقائمة الرئيسية تلقائياً)*"
                )
                user_mode[uid] = "usd_syp"
                bot.send_message(cid, reply, parse_mode="Markdown")
                bot.send_message(cid, format_bulletin(d), parse_mode="Markdown", reply_markup=main_keyboard(bot_username))
            except ValueError:
                bot.reply_to(message, "⚠️ يرجى إرسال رقم صحيح لعدد الغرامات (مثلاً: `5` أو `2.5`).")
            return

        try:
            amount = float(text.replace(",", ""))
            d = get_all_prices()
            rate_new = d["syp_sell_new"]

            if mode == "usd_syp":
                res_new = amount * rate_new
                res_old = int(res_new * 100)
                reply = f"💵 **حساب التحويل ({amount:,.2f} دولار أمريكي):**\n• بالليرة الجديدة: ` {res_new:,.2f} ` ل.س\n• بالليرة القديمة: ` {res_old:,} ` ل.س"
            elif mode == "syp_usd":
                usd_val = amount / (rate_new * 100) if amount >= 2000 else amount / rate_new
                reply = f"🇸🇾 **حساب التحويل ({amount:,.0f} ليرة سورية):**\n💵 القيمة بالدولار: **` {usd_val:,.2f} ` دولار**"
            elif mode == "try_syp":
                try_in_syp = rate_new / d["try_rate"]
                res_new = amount * try_in_syp
                res_old = int(res_new * 100)
                reply = f"🇹🇷 **حساب التحويل ({amount:,.2f} ليرة تركية):**\n• بالليرة الجديدة: ` {res_new:,.2f} ` ل.س\n• بالليرة القديمة: ` {res_old:,} ` ل.س"
            elif mode == "eur_syp":
                eur_in_syp = rate_new * (d["eur_usd"] / 100.0) if d["eur_usd"] > 10 else rate_new * d["eur_usd"]
                res_new = amount * eur_in_syp
                res_old = int(res_new * 100)
                reply = f"🇪🇺 **حساب التحويل ({amount:,.2f} يورو):**\n• بالليرة الجديدة: ` {res_new:,.2f} ` ل.س\n• بالليرة القديمة: ` {res_old:,} ` ل.س"
            else:
                res_new = amount * rate_new
                reply = f"💵 **النتيجة:** ` {res_new:,.2f} ` ل.س جديد"

            user_mode[uid] = "usd_syp"
            bot.send_message(cid, f"{reply}\n\n*(تم إرجاعك للقائمة الرئيسية تلقائياً)*", parse_mode="Markdown")
            bot.send_message(cid, format_bulletin(d), parse_mode="Markdown", reply_markup=main_keyboard(bot_username))
            
        except ValueError:
            bot.reply_to(message, "⚠️ عذراً، يرجى إرسال رقم صحيح للتحويل، أو استخدم الأزرار التفاعلية الموجودة أسفل النشرة.")

    if request.method == 'POST':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
        
    return "Syria Cash Pro - Running Smoothly 24/7!", 200
