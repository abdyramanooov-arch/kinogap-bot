import os
import sqlite3
import datetime
from threading import Thread
from flask import Flask
import telebot
from telebot import types

# ================= 1. SOZLAMALAR =================
TOKEN = '8886895047:AAFijeyfYPvn59YAcRvNKozxSTfIttACq2E'  # BotFather'dan olingan tokeningiz
ADMIN_ID = 7704099453        # Sizning Telegram ID'ingiz

bot = telebot.TeleBot(TOKEN)
DB_NAME = "kinogap.db"

admin_states = {}

# ================= 2. BEPUL FLASK SERVER =================
app = Flask('')

@app.route('/')
def home():
    return "KinoGap Bot faol ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# ================= 3. MA'LUMOTLAR BAZASI =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_vip INTEGER DEFAULT 0,
            joined_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            movie_code INTEGER PRIMARY KEY,
            file_id TEXT,
            caption TEXT
        )
    ''')
    # Kanallar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT,
            channel_name TEXT,
            channel_url TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def add_user(user_id, username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("INSERT INTO users (user_id, username, is_vip, joined_date) VALUES (?, ?, 0, ?)",
                       (user_id, username, today))
        conn.commit()
    conn.close()

# ================= 4. OBUNA TEKSHIRISH =================
def get_channels():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, channel_name, channel_url FROM channels")
    channels = cursor.fetchall()
    conn.close()
    return channels

def check_sub(user_id):
    channels = get_channels()
    unsubscribed = []
    for ch_id, ch_name, ch_url in channels:
        try:
            member = bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ['left', 'kicked']:
                unsubscribed.append((ch_name, ch_url))
        except Exception:
            # Bot kanalda admin bo'lmasa yoki xato bo'lsa
            pass
    return unsubscribed

def sub_keyboard(unsubscribed_channels):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for name, url in unsubscribed_channels:
        markup.add(types.InlineKeyboardButton(text=f"📢 {name}", url=url))
    markup.add(types.InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_subscription"))
    return markup

# ================= 5. MENULAR =================
def main_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎬 Kino qidirish", "💎 VIP Tarif")
    markup.row("📊 Statistika")
    if user_id == ADMIN_ID:
        markup.row("⚙️ Admin Panel")
    return markup

def admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add = types.InlineKeyboardButton("➕ Kino qo'shish", callback_data="add_movie")
    btn_del = types.InlineKeyboardButton("❌ Kino o'chirish", callback_data="del_movie")
    btn_ch = types.InlineKeyboardButton("📢 Kanallarni boshqarish", callback_data="manage_channels")
    btn_broadcast = types.InlineKeyboardButton("🚀 Xabar yuborish", callback_data="broadcast")
    btn_stats = types.InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")
    markup.add(btn_add, btn_del)
    markup.add(btn_ch)
    markup.add(btn_broadcast, btn_stats)
    return markup

# ================= 6. ASOSIY BUYRUQLAR =================
@bot.message_handler(commands=['start'])
def start_command(message):
    add_user(message.from_user.id, message.from_user.username)
    
    unsub = check_sub(message.from_user.id)
    if unsub:
        bot.send_message(
            message.chat.id, 
            "⚠️ **Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:**", 
            reply_markup=sub_keyboard(unsub),
            parse_mode="Markdown"
        )
        return

    text = f"👋 **Assalomu alaykum, {message.from_user.first_name}!**\n\n🎬 **KinoGap** botiga xush kelibsiz!\nKino ko'rish uchun **kino kodini** yuboring:"
    bot.send_message(message.chat.id, text, reply_markup=main_keyboard(message.from_user.id), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "⚙️ Admin Panel" and m.from_user.id == ADMIN_ID)
def admin_panel_msg(message):
    bot.send_message(message.chat.id, "🛠 **Admin Panelga xush kelibsiz!**\nKerakli bo'limni tanlang:", reply_markup=admin_keyboard(), parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def get_stats(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    u_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM movies")
    m_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE is_vip = 1")
    vip_count = cursor.fetchone()[0]
    conn.close()
    
    bot.send_message(
        message.chat.id, 
        f"📊 **Bot Statistikasi:**\n\n👤 Jami foydalanuvchilar: **{u_count} ta**\n💎 VIP a'zolar: **{vip_count} ta**\n🎬 Kinolar soni: **{m_count} ta**", 
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda m: m.text == "💎 VIP Tarif")
def vip_info(message):
    text = (
        "💎 **VIP Tarif imkoniyatlari:**\n\n"
        "✅ Reklamalarsiz va majburiy obunasiz tezkor yuklash\n"
        "✅ Eksklyuziv premyeralarga kirish\n\n"
        "💳 **Narxi:** 15,000 so'm / oyiga\n\n"
        "VIP-ga ulanish uchun admin bilan bog'laning: @admin_username"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎬 Kino qidirish")
def search_movie_hint(message):
    bot.send_message(message.chat.id, "🔍 Kino olish uchun shunchaki uning **kodini** yozib yuboring (masalan: `101`).", parse_mode="Markdown")

# ================= 7. CALLBACK HANDLER =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "check_subscription":
        unsub = check_sub(call.from_user.id)
        if unsub:
            bot.answer_callback_query(call.id, "❌ Hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)
            bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=sub_keyboard(unsub))
        else:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(
                call.message.chat.id, 
                "✅ **Rahmat! Barcha kanallarga obuna bo'ldingiz.**\nKino kodini yuborishingiz mumkin:", 
                reply_markup=main_keyboard(call.from_user.id),
                parse_mode="Markdown"
            )
        return

    if call.from_user.id != ADMIN_ID:
        return

    if call.data == "add_movie":
        admin_states[call.from_user.id] = "waiting_movie_code"
        bot.send_message(call.message.chat.id, "➕ Qo'shmoqchi bo'lgan kinongiz uchun **KOD** kiriting:")
    
    elif call.data == "del_movie":
        admin_states[call.from_user.id] = "waiting_del_code"
        bot.send_message(call.message.chat.id, "❌ O'chirmoqchi bo'lgan kino **kodini** kiriting:")

    elif call.data == "manage_channels":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("➕ Yangi kanal qo'shish", callback_data="add_channel"))
        
        channels = get_channels()
        for ch in channels:
            markup.add(types.InlineKeyboardButton(f"❌ O'chirish: {ch[1]}", callback_data=f"del_ch_{ch[0]}"))
        
        bot.send_message(call.message.chat.id, "📢 **Majburiy obuna kanallari:**", reply_markup=markup, parse_mode="Markdown")

    elif call.data == "add_channel":
        admin_states[call.from_user.id] = "waiting_channel_info"
        msg = (
            "➕ **Kanal qo'shish formati:**\n\n"
            "Ma'lumotlarni pastdagidek ko'rinishda kiriting:\n"
            "`Kanal_ID` | `Chiroyli Nom` | `Kanal_Havolasi`\n\n"
            "**Masalan:**\n"
            "`@-100123456789` | `DilNavo Uz` | `https://t.me/dilnavouz`"
        )
        bot.send_message(call.message.chat.id, msg, parse_mode="Markdown")

    elif call.data.startswith("del_ch_"):
        conn_id = call.data.replace("del_ch_", "")
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM channels WHERE channel_id = ?", (conn_id,))
        conn.commit()
        conn.close()
        bot.send_message(call.message.chat.id, "✅ Kanal obunalar ro'yxatidan o'chirildi!")

    elif call.data == "broadcast":
        admin_states[call.from_user.id] = "waiting_broadcast_msg"
        bot.send_message(call.message.chat.id, "📢 Tarqatmoqchi bo'lgan **xabaringizni** yuboring:")

    elif call.data == "admin_stats":
        get_stats(call.message)

# ================= 8. ADMIN INPUT HANDLERS =================
@bot.message_handler(content_types=['text', 'video', 'photo'], func=lambda m: m.from_user.id in admin_states)
def handle_admin_inputs(message):
    state = admin_states[message.from_user.id]
    
    # KANAL QO'SHISH
    if state == "waiting_channel_info":
        if "|" not in message.text:
            bot.send_message(message.chat.id, "⚠️ Noto'g'ri format! Format: `Kanal_ID | Nom | Havola`", parse_mode="Markdown")
            return
        parts = [p.strip() for p in message.text.split("|")]
        if len(parts) != 3:
            bot.send_message(message.chat.id, "⚠️ Iltimos, 3 ta ma'lumotni ham kiriting!")
            return
        
        ch_id, ch_name, ch_url = parts[0], parts[1], parts[2]
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO channels (channel_id, channel_name, channel_url) VALUES (?, ?, ?)",
                       (ch_id, ch_name, ch_url))
        conn.commit()
        conn.close()
        
        del admin_states[message.from_user.id]
        bot.send_message(message.chat.id, f"🎉 **{ch_name}** kanali muvaffaqiyatli qo'shildi!", parse_mode="Markdown")

    # KINO QO'SHISH - KOD
    elif state == "waiting_movie_code":
        if not message.text or not message.text.isdigit():
            bot.send_message(message.chat.id, "⚠️ Iltimos, faqat raqam kiriting!")
            return
        admin_states[f"{message.from_user.id}_code"] = int(message.text)
        admin_states[message.from_user.id] = "waiting_movie_file"
        bot.send_message(message.chat.id, f"✅ Kod: {message.text}. Endi **videoni** yuboring:")

    # KINO QO'SHISH - VIDEO
    elif state == "waiting_movie_file":
        if message.content_type != 'video':
            bot.send_message(message.chat.id, "⚠️ Video yuboring!")
            return
        movie_code = admin_states.get(f"{message.from_user.id}_code")
        file_id = message.video.file_id
        caption = message.caption if message.caption else f"🎬 Kino kodi: {movie_code}"
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO movies (movie_code, file_id, caption) VALUES (?, ?, ?)",
                       (movie_code, file_id, caption))
        conn.commit()
        conn.close()
        
        del admin_states[message.from_user.id]
        del admin_states[f"{message.from_user.id}_code"]
        bot.send_message(message.chat.id, f"🎉 Kino saqlandi! Kodi: `{movie_code}`", parse_mode="Markdown")

    # KINO O'CHIRISH
    elif state == "waiting_del_code":
        if not message.text or not message.text.isdigit():
            bot.send_message(message.chat.id, "⚠️ Faqat raqam kiriting!")
            return
        m_code = int(message.text)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movies WHERE movie_code = ?", (m_code,))
        changes = conn.total_changes
        conn.commit()
        conn.close()
        
        del admin_states[message.from_user.id]
        bot.send_message(message.chat.id, f"🗑 Kod `{m_code}` bo'lgan kino o'chirildi!", parse_mode="Markdown")

    # XABAR TARQATISH
    elif state == "waiting_broadcast_msg":
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()
        
        count = 0
        bot.send_message(message.chat.id, "🚀 Xabar yuborish boshlandi...")
        for user in users:
            try:
                bot.copy_message(chat_id=user[0], from_chat_id=message.chat.id, message_id=message.message_id)
                count += 1
            except Exception:
                pass
        
        del admin_states[message.from_user.id]
        bot.send_message(message.chat.id, f"✅ Xabar **{count} ta** foydalanuvchiga yuborildi!", parse_mode="Markdown")

# ================= 9. KINO KODI BO'YICHA YUBORISH =================
@bot.message_handler(func=lambda m: m.text and m.text.isdigit())
def send_movie_by_code(message):
    unsub = check_sub(message.from_user.id)
    if unsub:
        bot.send_message(
            message.chat.id, 
            "⚠️ **Kino olish uchun avval kanallarga obuna bo'ling:**", 
            reply_markup=sub_keyboard(unsub),
            parse_mode="Markdown"
        )
        return

    code = int(message.text)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, caption FROM movies WHERE movie_code = ?", (code,))
    movie = cursor.fetchone()
    conn.close()
    
    if movie:
        bot.send_video(message.chat.id, video=movie[0], caption=f"{movie[1]}\n\n🤖 @KinoGapBot")
    else:
        bot.send_message(message.chat.id, f"❌ `{code}` kodli kino topilmadi.", parse_mode="Markdown")

# ================= 10. ISHGA TUSHIRISH =================
if __name__ == "__main__":
    keep_alive()
    print("KinoGap Bot ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
        
