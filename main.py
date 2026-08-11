import sqlite3
import datetime
import telebot
from telebot import types

# ================= SOZLAMALAR =================
TOKEN = '8886895047:AAHXuiBlGpdqZA9GO-5WOsM5xOV52R-rI4M'  # BotFather tokeningiz
ADMIN_ID = 7704099453        # Sizning Telegram ID'ingiz

bot = telebot.TeleBot(TOKEN)
DB_NAME = "kinogap.db"

# ================= MA'LUMOTLAR BAZASI =================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
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
    conn.commit()
    conn.close()

init_db()

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

# ================= BUYRUQLAR VA MENU =================
@bot.message_handler(commands=['start'])
def start_command(message):
    add_user(message.from_user.id, message.from_user.username)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎬 Kino qidirish", "📊 Statistika")
    
    text = f"👋 **Assalomu alaykum!**\n\n🎬 **KinoGap** botiga xush kelibsiz!\nKino ko'rish uchun **kino kodini** yuboring:"
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📊 Statistika")
def get_stats(message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    u_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM movies")
    m_count = cursor.fetchone()[0]
    conn.close()
    
    bot.send_message(
        message.chat.id, 
        f"📊 **Statistika:**\n\n👤 Foydalanuvchilar: **{u_count} ta**\n🎬 Kinolar: **{m_count} ta**", 
        parse_mode="Markdown"
    )

# ================= ISHGA TUSHIRISH =================
if __name__ == "__main__":
    print("KinoGap Bot ishga tushdi...")
    bot.infinity_polling(skip_pending_subscriptions=True)
    
