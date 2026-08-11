import telebot
from telebot import types
import sqlite3
import datetime
import os
from threading import Thread
from flask import Flask

# --- SOZLAMALAR ---
TOKEN = '8871158703:AAFB7mug0siDuKcRJ5ZgOrh8Xa7XemYTrVk'  # BotFather'dan olingan token
ADMIN_ID = 7704099453        # Admin Telegram ID'si

# Majburiy obuna kanallari (Kanal ID'si yoki username'i)
CHANNELS = ["@KinoGap_Official"]  # Masalan: ["@kanal1", "@kanal2"]

bot = telebot.TeleBot(TOKEN)
DB_NAME = "kinogap.db"

# --- FLASK VEB-SERVER (Render Port Xatosini Oldini Olish Uchun) ---
app = Flask('')

@app.route('/')
def home():
    return "KinoGap Bot faol va ishlamoqda!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# --- MA'LUMOTLAR BAZASI ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Foydalanuvchilar jadvali
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            joined_date TEXT,
            is_vip INTEGER DEFAULT 0
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

# --- MAJBURIY OBUNA TEKSHIRUVI ---
def check_sub(user_id):
    for ch in CHANNELS:
        try:
            member = bot.get_chat_member(ch, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            pass
    return True

def sub_keyboard():
    markup = types.InlineKeyboardMarkup()
    for ch in CHANNELS:
        ch_url = f"https://t.me/{ch.replace('@', '')}"
        markup.add(types.InlineKeyboardButton("📢 Kanalga a'zo bo'lish", url=ch_url))
    markup.add(types.InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_subscription"))
    return markup

# --- FOYDALANUVCHINI BAZAGA QO'SHISH ---
def add_user(user_id, username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        cursor.execute("INSERT INTO users (user_id, username, joined_date) VALUES (?, ?, ?)",
                       (user_id, username, today))
        conn.commit()
    conn.close()

# --- COMMANDS ---

@bot.message_handler(commands=['start'])
def start_command(message):
    add_user(message.from_user.id, message.from_user.username)
    
    if not check_sub(message.from_user.id):
        bot.send_message(
            message.chat.id, 
            "⚠️ **Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:**", 
            reply_markup=sub_keyboard(), 
            parse_mode="Markdown"
        )
        return

    send_main_menu(message.chat.id, message.from_user.first_name)

def send_main_menu(chat_id, name):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎬 Kino qidirish", "⭐️ VIP Obuna")
    markup.row("📊 Statistika", "📞 Aloqa")
    
    text = f"👋 **Assalomu alaykum, {name}!**\n\n🎬 **KinoGap** botiga xush kelibsiz!\nKino ko'rish uchun **kino kodini** yuboring:"
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_sub_callback(call):
    if check_sub(call.from_user.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_main_menu(call.message.chat.id, call.from_user.first_name)
    else:
        bot.answer_callback_query(call.id, "❌ Hali hamma kanallarga a'zo bo'lmadingiz!", show_alert=True)

# --- ADMIN PANEL ---

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("➕ Kino qo'shish", callback_data="add_movie")
        btn2 = types.InlineKeyboardButton("🗑 Kino o'chirish", callback_data="del_movie")
        btn3 = types.InlineKeyboardButton("📢 Xabar tarqatish", callback_data="broadcast")
        markup.add(btn1, btn2, btn3)
        bot.send_message(message.chat.id, "🛠 **Admin panel:**", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data in ["add_movie", "del_movie", "broadcast"])
def admin_actions(call):
    if call.from_user.id != ADMIN_ID:
        return
        
    if call.data == "add_movie":
        msg = bot.send_message(call.message.chat.id, "📥 **Kino videosini yuboring va izohga (caption) KINO KODINI yozing:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_add_movie)
        
    elif call.data == "del_movie":
        msg = bot.send_message(call.message.chat.id, "🗑 **O'chirmoqchi bo'lgan kino kodini yozing:**", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_del_movie)
        
    elif call.data == "broadcast":
        msg = bot.send_message(call.message.chat.id, "📢 **Barcha foydalanuvchilarga yuboriladigan xabarni (matn, rasm yoki video) yuboring:**")
        bot.register_next_step_handler(msg, process_broadcast)

# Admin: Kino qo'shish
def process_add_movie(message):
    if message.content_type == 'video':
        file_id = message.video.file_id
        try:
            movie_code = int(message.caption)
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("INSERT OR REPLACE INTO movies (movie_code, file_id, caption) VALUES (?, ?, ?)",
                           (movie_code, file_id, f"Kino kodi: {movie_code}"))
            conn.commit()
            conn.close()
            bot.send_message(message.chat.id, f"✅ Kino **{movie_code}** kodi bilan bazaga saqlandi!")
        except Exception:
            bot.send_message(message.chat.id, "❌ Xatolik: Video izohiga faqat **raqam (kino kodi)** yozing!")
    else:
        bot.send_message(message.chat.id, "❌ Faqat video fayl yuboring!")

# Admin: Kino o'chirish
def process_del_movie(message):
    if message.text and message.text.isdigit():
        code = int(message.text)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM movies WHERE movie_code = ?", (code,))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ **{code}**-kodli kino o'chirildi!")
    else:
        bot.send_message(message.chat.id, "❌ Faqat raqam yuboring!")

# Admin: Broadcast (Xabar tarqatish)
def process_broadcast(message):
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
    bot.send_message(message.chat.id, f"✅ Xabar **{count}** ta foydalanuvchiga muvaffaqiyatli yetkazildi!")

# --- MENU BUTTONS ---

@bot.message_handler(func=lambda message: message.text == "📊 Statistika")
def get_stats(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    u_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM movies")
    m_count = cursor.fetchone()[0]
    conn.close()
    
    text = (
        f"📊 **KinoGap Bot Statistikasi:**\n\n"
        f"👤 Jami foydalanuvchilar: **{u_count} ta**\n"
        f"🎬 Jami yuklangan kinolar: **{m_count} ta**"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "⭐️ VIP Obuna")
def vip_info(message):
    text = (
        "⭐️ **VIP TARIF REJALARI:**\n\n"
        "1️⃣ **1 Oylik VIP** - 15,000 so'm\n"
        "2️⃣ **3 Oylik VIP** - 35,000 so'm\n"
        "3️⃣ **Umrbod VIP** - 80,000 so'm\n\n"
        "✨ **VIP afzalliklari:**\n"
        "• Reklamalarsiz tezkor ko'rish\n"
        "• Premium kino va seriallar bazasi\n\n"
        "💳 Xarid qilish uchun Adminga murojaat qiling: @abdyramanooov"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📞 Aloqa")
def contact_admin(message):
    bot.send_message(message.chat.id, "📞 Admin bilan bog'lanish: @abdyramanooov")

# --- KINO QIDIRISH (KOD BO'YICHA) ---

@bot.message_handler(func=lambda message: message.text.isdigit())
def search_movie(message):
    if not check_sub(message.from_user.id):
        bot.send_message(message.chat.id, "⚠️ Kinoni ko'rish uchun avval kanallarga a'zo bo'ling!", reply_markup=sub_keyboard())
        return
        
    code = int(message.text)
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, caption FROM movies WHERE movie_code = ?", (code,))
    res = cursor.fetchone()
    conn.close()
    
    if res:
        bot.send_video(message.chat.id, res[0], caption=f"🎬 **Kino kodi:** {code}\n\n{res[1] if res[1] else ''}", parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, f"❌ **{code}** kodli kino topilmadi.")

# --- BOTNI ISHGA TUSHIRISH ---
if __name__ == "__main__":
    keep_alive()  # Web serverni fonda ishga tushirish (Render port xatosi bermasligi uchun)
    print("KinoGap Bot ishga tushdi...")
    bot.polling(none_stop=True)
