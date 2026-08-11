import os
import sqlite3
import datetime
from threading import Thread
from flask import Flask
import telebot
from telebot import types

# ================= 1. SOZLAMALAR =================
TOKEN = '8886895047:AAFijeyfYPvn59YAcRvNKozxSTfIttACq2E'  # BotFather'dan olingan to'liq tokeningiz
ADMIN_ID = 7704099453        # Sizning Telegram ID'ingiz

bot = telebot.TeleBot(TOKEN)
DB_NAME = "kinogap.db"

# Admin xolatlarini saqlash uchun
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
    # Foydalanuvchilar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            is_vip INTEGER DEFAULT 0,
            joined_date TEXT
        )
    ''')
    # Kinolar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movies (
            movie_code INTEGER PRIMARY KEY,
            file_id TEXT,
            caption TEXT
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

# ================= 4. MENULAR =================
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
    btn_broadcast = types.InlineKeyboardButton("📢 Xabar yuborish", callback_data="broadcast")
    btn_stats = types.InlineKeyboardButton("📊 Statistika", callback_data="admin_stats")
    markup.add(btn_add, btn_del, btn_broadcast, btn_stats)
    return markup

# ================= 5. ASOSIY BUYRUQLAR =================
@bot.message_handler(commands=['start'])
def start_command(message):
    add_user(message.from_user.id, message.from_user.username)
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
        "✅ Reklamalarsiz tezkor kino yuklash\n"
        "✅ Eksklyuziv kinolar va premyeralarga kirish\n"
        "✅ 24/7 shaxsiy yordam\n\n"
        "💳 **Narxi:** 15,000 so'm / oyiga\n\n"
        "VIP-ga ulanish uchun admin bilan bog'laning: @admin_username"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎬 Kino qidirish")
def search_movie_hint(message):
    bot.send_message(message.chat.id, "🔍 Kino olish uchun shunchaki uning **kodini** yozib yuboring (masalan: `101`).", parse_mode="Markdown")

# ================= 6. INLINE TUGMALAR (CALLBACKS) =================
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.from_user.id != ADMIN_ID:
        return
    
    if call.data == "add_movie":
        admin_states[call.from_user.id] = "waiting_movie_code"
        bot.send_message(call.message.chat.id, "➕ Qo'shmoqchi bo'lgan kinongiz uchun **KOD** kiriting (masalan: 101):")
    
    elif call.data == "del_movie":
        admin_states[call.from_user.id] = "waiting_del_code"
        bot.send_message(call.message.chat.id, "❌ O'chirmoqchi bo'lgan kino **kodini** kiriting:")
        
    elif call.data == "broadcast":
        admin_states[call.from_user.id] = "waiting_broadcast_msg"
        bot.send_message(call.message.chat.id, "📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan **xabaringizni** (matn, rasm yoki video) yuboring:")
        
    elif call.data == "admin_stats":
        get_stats(call.message)

# ================= 7. ADMIN VA KINO QIDIRISH HANDLERLARI =================
@bot.message_handler(content_types=['text', 'video', 'photo'], func=lambda m: m.from_user.id in admin_states)
def handle_admin_inputs(message):
    state = admin_states[message.from_user.id]
    
    # 1. KINO QO'SHISH - KOD
    if state == "waiting_movie_code":
        if not message.text or not message.text.isdigit():
            bot.send_message(message.chat.id, "⚠️ Iltimos, faqat raqamlardan iborat kod kiriting!")
            return
        admin_states[f"{message.from_user.id}_code"] = int(message.text)
        admin_states[message.from_user.id] = "waiting_movie_file"
        bot.send_message(message.chat.id, f"✅ Kod: {message.text}. Endi shu kinoning **videosini** yuboring:")
    
    # 2. KINO QO'SHISH - VIDEO
    elif state == "waiting_movie_file":
        if message.content_type != 'video':
            bot.send_message(message.chat.id, "⚠️ Iltimos, video fayl yuboring!")
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
        bot.send_message(message.chat.id, f"🎉 **Kino muvaffaqiyatli saqlandi!**\nKodi: `{movie_code}`", parse_mode="Markdown")

    # 3. KINO O'CHIRISH
    elif state == "waiting_del_code":
        if not message.text or not message.text.isdigit():
            bot.send_message(message.chat.id, "⚠️ Iltimos, faqat raqam kiriting!")
            return
        
        m_code = int(message.text)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movies WHERE movie_code = ?", (m_code,))
        changes = conn.total_changes
        conn.commit()
        conn.close()
        
        del admin_states[message.from_user.id]
        if changes > 0:
            bot.send_message(message.chat.id, f"🗑 Kod `{m_code}` bo'lgan kino o'chirildi!", parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, f"⚠️ Kodingiz `{m_code}` bo'yicha kino topilmadi.", parse_mode="Markdown")

    # 4. RASSILKA (XABAR YUBORISH)
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
        bot.send_message(message.chat.id, f"✅ Xabar **{count} ta** foydalanuvchiga muvaffaqiyatli yuborildi!", parse_mode="Markdown")

# ================= 8. KINO KODI BO'YICHA YUBORISH =================
@bot.message_handler(func=lambda m: m.text and m.text.isdigit())
def send_movie_by_code(message):
    code = int(message.text)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, caption FROM movies WHERE movie_code = ?", (code,))
    movie = cursor.fetchone()
    conn.close()
    
    if movie:
        bot.send_video(message.chat.id, video=movie[0], caption=f"{movie[1]}\n\n🤖 @KinoGapBot - Barcha kinolar shu yerda!")
    else:
        bot.send_message(message.chat.id, f"❌ Afsuski, `{code}` kodli kino topilmadi.", parse_mode="Markdown")

# ================= 9. ISHGA TUSHIRISH =================
if __name__ == "__main__":
    keep_alive()
    print("KinoGap Bot ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
        
