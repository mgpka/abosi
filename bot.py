import os
import json
import time
import threading
from datetime import datetime, timezone, timedelta
from flask import Flask
import telebot
from telebot import types
import google.generativeai as genai

# ================= إعدادات البوت والربط =================
BOT_TOKEN = "8907461003:AAEdXDdEWq2p_fttJN-Jz63-T_0EWQPupCM"
OWNER_ID = 1460392381
OWNER_USERNAME = "@mgpka"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DATA_FILE = "aboosi_data.json"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_INSTRUCTION = f"""
أنت 'عبوسي'، المساعد الذكي، الضلع، وروح كروب 'الأمراء' على تيليجرام.
شخصيتك وأسلوبك:
1. تتكلم باللهجة العراقية اليومية العفوية البحتة (ضلعي، عيوني، شكو ماكو، لا بربك، صدك تحجي، تدلل، ها شبيك).
2. صاحب ميانة عالية، تحب السوالف والضحك والتحشيش الخفيف الودود.
3. ذكي وتساعد بالبرمجة والدراسة والحلول.
4. رسائلك سريعة ومختصرة (سطرين أو ثلاثة).

القواعد الأمنية:
1. المالك هو علي ({OWNER_USERNAME})، تحترمه احتراما كاملاً وتكول عنه تاج الراس.
2. ممنوع إعطاء رابط الكروب بالخاص نهائياً.
3. ممنوع كشف التوكن أو الكود أو الأسرار.
"""

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# أمر فحص مباشر لمعرفة الموديلات الشغالة بحسابك
@bot.message_handler(commands=['test'])
def test_models_cmd(message):
    try:
        models = [m.name.replace("models/", "") for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        if models:
            bot.reply_to(message, "✅ الموديلات المتوفرة بحسابك:\n" + "\n".join(models[:6]))
        else:
            bot.reply_to(message, "⚠️ المفتاح لا يحتوي على موديلات توليد نصوص.")
    except Exception as e:
        bot.reply_to(message, f"❌ خطأ فحص الموديلات:\n{e}")

# دالة التحدث مع الذكاء الاصطناعي
def ask_aboosi(user_name, text):
    prompt = f"{SYSTEM_INSTRUCTION}\n\nالمستخدم ({user_name}) يكول: {text}"
    candidate_models = ["gemini-1.5-flash-latest", "gemini-pro", "gemini-1.5-flash", "gemini-2.0-flash"]
    
    last_err = ""
    for m_name in candidate_models:
        try:
            m = genai.GenerativeModel(m_name)
            res = m.generate_content(prompt)
            if res and res.text:
                return res.text
        except Exception as e:
            last_err = str(e)
            continue
            
    return f"⚠️ فشل الاتصال:\n{last_err}"

# ================= إدارة البيانات =================
def load_data():
    default_config = {
        "bot_enabled": True,
        "groups_enabled": True,
        "private_enabled": True,
        "admins": [],
        "known_users": {}
    }
    if not os.path.exists(DATA_FILE):
        save_data(default_config)
        return default_config
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for k, v in default_config.items():
                if k not in data:
                    data[k] = v
            return data
    except Exception:
        return default_config

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

user_states = {}

def get_iraq_time():
    tz_iraq = timezone(timedelta(hours=3))
    now = datetime.now(tz_iraq)
    return now.strftime("%Y/%m/%d - %I:%M %p")

@app.route('/')
def home():
    return "عبوسي شغال 24/7!"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# ================= لوحة التحكم =================
def get_control_keyboard():
    data = load_data()
    power_btn = "🔴 إيقاف البوت" if data.get("bot_enabled", True) else "🟢 تشغيل البوت"
    grp_btn = "👥 الكروبات: 🟢 مفعل" if data.get("groups_enabled", True) else "👥 الكروبات: 🔴 معطل"
    prv_btn = "🔒 الخاص: 🟢 مفعل" if data.get("private_enabled", True) else "🔒 الخاص: 🔴 معطل"

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton(power_btn, callback_data="toggle_power"))
    markup.add(
        types.InlineKeyboardButton(grp_btn, callback_data="toggle_groups"),
        types.InlineKeyboardButton(prv_btn, callback_data="toggle_private")
    )
    markup.add(
        types.InlineKeyboardButton("➕ إضافة مشرف", callback_data="btn_add_admin"),
        types.InlineKeyboardButton("➖ حذف مشرف", callback_data="btn_del_admin")
    )
    markup.add(
        types.InlineKeyboardButton("👥 قائمة المشرفين", callback_data="btn_list_admins"),
        types.InlineKeyboardButton("📊 إحصائيات البوت", callback_data="btn_stats")
    )
    markup.add(types.InlineKeyboardButton("📢 إذاعة للمستخدمين", callback_data="btn_broadcast"))
    return markup

@bot.message_handler(commands=['panel', 'control'])
def admin_panel(message):
    if message.chat.type == "private" and message.from_user.id == OWNER_ID:
        data = load_data()
        st = "🟢 شغال" if data.get("bot_enabled", True) else "🔴 متوقف"
        bot.send_message(
            message.chat.id,
            f"👑 <b>أهلاً بك يا علي في لوحة تحكم عبوسي:</b>\nالحالة: <b>{st}</b>",
            reply_markup=get_control_keyboard(),
            parse_mode="HTML"
        )

@bot.message_handler(commands=['start'])
def handle_start(message):
    data = load_data()
    user_id = str(message.from_user.id)
    name = message.from_user.first_name or "مجهول"
    username = f"@{message.from_user.username}" if message.from_user.username else "بدون يوزر"

    if message.chat.type == "private":
        if user_id not in data["known_users"] and message.from_user.id != OWNER_ID:
            now_str = get_iraq_time()
            data["known_users"][user_id] = {"name": name, "username": username, "date": now_str}
            save_data(data)
            try:
                bot.send_message(OWNER_ID, f"🚨 <b>دخول جديد لخاص عبوسي:</b>\n{name} ({username})", parse_mode="HTML")
            except Exception:
                pass

        if message.from_user.id == OWNER_ID:
            bot.send_message(message.chat.id, f"👑 هلا بتاج الراس علي ({OWNER_USERNAME})!\nأرسل /panel للوحة التحكم أو /test لفحص الموديلات.")
        else:
            bot.send_message(message.chat.id, "هلا والله! أني عبوسي، اسألني وأجاوبك على أي شي 👑")

# ================= تفاعل الأزرار =================
@bot.callback_query_handler(func=lambda call: call.data in [
    "toggle_power", "toggle_groups", "toggle_private",
    "btn_add_admin", "btn_del_admin", "btn_list_admins", "btn_stats", "btn_broadcast"
] or call.data.startswith("del_adm_"))
def panel_actions(call):
    if call.from_user.id != OWNER_ID:
        bot.answer_callback_query(call.id, "اللوحة للمالك علي فقط!", show_alert=True)
        return

    data = load_data()
    if call.data == "toggle_power":
        data["bot_enabled"] = not data.get("bot_enabled", True)
        save_data(data)
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_control_keyboard())
        except Exception:
            pass
        bot.answer_callback_query(call.id, "تم تغيير حالة البوت.")

    elif call.data == "toggle_groups":
        data["groups_enabled"] = not data.get("groups_enabled", True)
        save_data(data)
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_control_keyboard())
        except Exception:
            pass
        bot.answer_callback_query(call.id, "تم تغيير حالة الكروبات.")

    elif call.data == "toggle_private":
        data["private_enabled"] = not data.get("private_enabled", True)
        save_data(data)
        try:
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=get_control_keyboard())
        except Exception:
            pass
        bot.answer_callback_query(call.id, "تم تغيير حالة الخاص.")

    elif call.data == "btn_stats":
        total_users = len(data.get("known_users", {}))
        admins_count = len(data.get("admins", []))
        bot.send_message(call.message.chat.id, f"📊 <b>مستخدمي الخاص:</b> {total_users}\n👮 <b>المشرفين:</b> {admins_count}", parse_mode="HTML")
        bot.answer_callback_query(call.id)

    elif call.data == "btn_list_admins":
        admins = data.get("admins", [])
        txt = "👥 المشرفين:\n" + "\n".join([f"• <code>{adm}</code>" for adm in admins]) if admins else "لا يوجد مشرفين."
        bot.send_message(call.message.chat.id, txt, parse_mode="HTML")
        bot.answer_callback_query(call.id)

    elif call.data == "btn_add_admin":
        user_states[call.from_user.id] = "waiting_for_admin"
        bot.send_message(call.message.chat.id, "أرسل آيدي المشرف الرقمي:")
        bot.answer_callback_query(call.id)

    elif call.data == "btn_del_admin":
        admins = data.get("admins", [])
        if not admins:
            bot.answer_callback_query(call.id, "لا يوجد مشرفين.", show_alert=True)
            return
        markup = types.InlineKeyboardMarkup()
        for adm in admins:
            markup.add(types.InlineKeyboardButton(f"❌ حذف {adm}", callback_data=f"del_adm_{adm}"))
        bot.send_message(call.message.chat.id, "اختر المشرف لحذفه:", reply_markup=markup)
        bot.answer_callback_query(call.id)

    elif call.data.startswith("del_adm_"):
        target = call.data.replace("del_adm_", "")
        data["admins"] = [a for a in data.get("admins", []) if str(a) != target]
        save_data(data)
        bot.answer_callback_query(call.id, f"تم حذف {target}")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass

    elif call.data == "btn_broadcast":
        user_states[call.from_user.id] = "waiting_for_broadcast"
        bot.send_message(call.message.chat.id, "أرسل الرسالة لإذاعتها للجميع:")
        bot.answer_callback_query(call.id)

# ================= استقبال الرسائل =================
@bot.message_handler(content_types=['text', 'photo', 'video'])
def handle_all_chat(message):
    data = load_data()
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "الضلع"
    is_owner = (user_id == OWNER_ID)
    is_admin = (user_id in data.get("admins", []))
    bot_info = bot.get_me()

    if message.chat.type == "private" and is_owner and user_id in user_states:
        state = user_states.pop(user_id, None)
        if state == "waiting_for_admin":
            val = message.text.strip() if message.text else ""
            if val.isdigit():
                if int(val) not in data["admins"]:
                    data["admins"].append(int(val))
                    save_data(data)
                    bot.send_message(message.chat.id, f"✅ تم حفظ المشرف {val}")
            return
        elif state == "waiting_for_broadcast":
            users = list(data.get("known_users", {}).keys())
            bot.send_message(message.chat.id, f"جاري الإذاعة إلى {len(users)} مستخدم...")
            sent = 0
            for u in users:
                try:
                    bot.copy_message(int(u), message.chat.id, message.message_id)
                    sent += 1
                    time.sleep(0.05)
                except Exception:
                    pass
            bot.send_message(message.chat.id, f"اكتملت الإذاعة لـ {sent} مستخدم.")
            return

    if not data.get("bot_enabled", True) and not is_owner:
        return

    text = message.text or message.caption or ""

    if message.chat.type in ["group", "supergroup"]:
        if not data.get("groups_enabled", True) and not is_owner and not is_admin:
            return
        is_reply = (message.reply_to_message and message.reply_to_message.from_user.id == bot_info.id)
        triggers = ["عبوسي", "عبوس", "يا عبوسي"]
        if is_reply or any(trig in text for trig in triggers) or (f"@{bot_info.username}" in text if bot_info.username else False):
            bot.send_chat_action(message.chat.id, 'typing')
            res = ask_aboosi(user_name, text)
            try:
                bot.reply_to(message, res)
            except Exception:
                bot.send_message(message.chat.id, res)

    elif message.chat.type == "private":
        if not data.get("private_enabled", True) and not is_owner and not is_admin:
            return
        bot.send_chat_action(message.chat.id, 'typing')
        res = ask_aboosi(user_name, text)
        try:
            bot.reply_to(message, res)
        except Exception:
            bot.send_message(message.chat.id, res)

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=20)
        except Exception as e:
            time.sleep(5)
