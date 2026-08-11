import telebot
from telebot import types
import sqlite3
import requests
import re
import datetime
import yt_dlp
import os

# --- SOZLAMALAR ---
TOKEN = '8871158703:AAFB7mug0siDuKcRJ5ZgOrh8Xa7XemYTrVk' # BotFather'dan olingan token
ADMIN_ID = 7704099453  # Telegram ID raqamingiz
bot = telebot.TeleBot(TOKEN)

# RegEx patternlar
TIKTOK_PATTERN = r'(https?://(?:www\.|vt\.|vm\.)?tiktok\.com/[^\s]+)'
INSTAGRAM_PATTERN = r'(https?://(?:www\.)?instagram\.com/(?:p|reel|reels)/[^\s]+)'

# --- BAZA BILAN ISHLASH ---
def init_db():
    conn = sqlite3.connect("teezsaqla.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            vip_until TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            channel_id TEXT PRIMARY KEY,
            name TEXT,
            invite_link TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def add_user(user_id):
    conn = sqlite3.connect("teezsaqla.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, vip_until) VALUES (?, ?)", (user_id, "NONE"))
    conn.commit()
    conn.close()

def is_vip(user_id):
    if user_id == ADMIN_ID:
        return True
    conn = sqlite3.connect("teezsaqla.db")
    cursor = conn.cursor()
    cursor.execute("SELECT vip_until FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row[0] != "NONE":
        try:
            vip_date = datetime.datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
            if datetime.datetime.now() < vip_date:
                return True
        except:
            return False
    return False

def add_vip(user_id, days):
    conn = sqlite3.connect("teezsaqla.db")
    cursor = conn.cursor()
    until = (datetime.datetime.now() + datetime.timedelta(days=int(days))).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT OR REPLACE INTO users (user_id, vip_until) VALUES (?, ?)", (user_id, until))
    conn.commit()
    conn.close()

def get_users_list():
    conn = sqlite3.connect("teezsaqla.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

def add_channel(channel_id, name, invite_link):
    conn = sqlite3.connect("teezsaqla.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO channels (channel_id, name, invite_link) VALUES (?, ?, ?)", 
                   (channel_id, name, invite_link))
    conn.commit()
    conn.close()

def delete_channel(channel_id):
    conn = sqlite3.connect("teezsaqla.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
    conn.commit()
    conn.close()

def get_channels():
    conn = sqlite3.connect("teezsaqla.db")
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, name, invite_link FROM channels")
    rows = cursor.fetchall()
    conn.close()
    return rows

def check_sub(user_id, channel_id):
    try:
        member = bot.get_chat_member(channel_id, user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
    except:
        return False
    return False

def send_sub_menu(chat_id):
    if is_vip(chat_id):
        return True
    channels = get_channels()
    unsubscribed = []
    for ch_id, ch_name, ch_link in channels:
        if not check_sub(chat_id, ch_id):
            unsubscribed.append((ch_name, ch_link))
    if not unsubscribed:
        return True
    keyboard = types.InlineKeyboardMarkup()
    for name, link in unsubscribed:
        keyboard.add(types.InlineKeyboardButton(f"📢 {name}", url=link))
    keyboard.add(types.InlineKeyboardButton("Tekshirish ✅", callback_data="check_subscription"))
    bot.send_message(chat_id, "⚠️ **Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:**", 
                     parse_mode="Markdown", reply_markup=keyboard)
    return False

def download_instagram(url):
    clean_url = url.split("?")[0]
    output_filename = f"ig_{datetime.datetime.now().timestamp()}.mp4"
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'outtmpl': output_filename,
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([clean_url])
            if os.path.exists(output_filename):
                return output_filename, "file"
    except Exception as e:
        if os.path.exists(output_filename):
            os.remove(output_filename)

    try:
        api_url = f"https://v3.tikwm.com/api/download?url={clean_url}"
        res = requests.get(api_url, timeout=10).json()
        if "data" in res and "play" in res["data"]:
            return res["data"]["play"], "url"
    except Exception as e:
        pass

    return None, None

def download_tiktok(url):
    try:
        clean_url = url.split("?")[0]
        api_url = f"https://www.tikwm.com/api/?url={clean_url}"
        res = requests.get(api_url, timeout=10).json()
        if res.get("code") == 0:
            data = res.get("data", {})
            video = data.get("play")
            audio = data.get("music")
            title = data.get("title", "TikTok Music")
            return video, audio, title
    except Exception as e:
        pass
    return None, None, None

@bot.message_handler(commands=['start'])
def start_cmd(message):
    add_user(message.from_user.id)
    if send_sub_menu(message.chat.id):
        vip_status = "⭐ **Siz VIP foydalanuvchisiz!**" if is_vip(message.from_user.id) else ""
        welcome = (
            f"👋 **Assalomu alaykum! TeezSaqlaBot'ga xush kelibsiz!**\n\n"
            f"{vip_status}\n\n"
            "📥 **TikTok** yoki **Instagram** video havolasini yuboring."
        )
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("⭐ VIP Tarif haqida")
        bot.send_message(message.chat.id, welcome, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "⭐ VIP Tarif haqida")
def vip_info(message):
    text = (
        "⭐ **VIP Tarif imkoniyatlari:**\n\n"
        "1. Majburiy obunalarsiz botdan cheksiz foydalanish.\n"
        "2. Videolarni reklamasiz va tezroq yuklab olish.\n\n"
        "💳 **VIP xarid qilish uchun admin bilan bog'laning:** @admin_username"
    )
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def check_sub_callback(call):
    if send_sub_menu(call.message.chat.id):
        bot.answer_callback_query(call.id, "✅ Obuna tasdiqlandi!")
        try: bot.delete_message(call.message.chat.id, call.message.message_id)
        except: pass
        bot.send_message(call.message.chat.id, "📥 Endi video havolasini yuborishingiz mumkin!")
    else:
        bot.answer_callback_query(call.id, "❌ Hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID: return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📢 Kanal qo'shish", "❌ Kanalni o'chirish")
    markup.row("⭐ VIP Berish", "📊 Statistika")
    markup.row("✉️ Xabar yuborish (Rassilka)")
    bot.send_message(message.chat.id, "🛠 **Admin panel:**", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "📊 Statistika")
def show_stats(message):
    if message.from_user.id != ADMIN_ID: return
    users = get_users_list()
    channels = get_channels()
    bot.send_message(message.chat.id, f"👥 **Baza a'zolari:** {len(users)} ta\n📢 **Majburiy kanallar:** {len(channels)} ta", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "📢 Kanal qo'shish")
def ask_channel(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(message.chat.id, "Format: `Nomi | ID/Username | Link`\nMasalan: `TeezSaqla | @teezsaqla | https://t.me/teezsaqla`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, save_channel)

def save_channel(message):
    try:
        data = message.text.split("|")
        name, ch_id, link = [i.strip() for i in data]
        add_channel(ch_id, name, link)
        bot.send_message(message.chat.id, f"✅ Kanal qo'shildi: **{name}**", parse_mode="Markdown")
    except:
        bot.send_message(message.chat.id, "❌ Noto'g'ri format!")

@bot.message_handler(func=lambda m: m.text == "❌ Kanalni o'chirish")
def ask_del_channel(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(message.chat.id, "O'chirmoqchi bo'lgan kanal ID/Username'ini yuboring (Masalan: `@teezsaqla`):")
    bot.register_next_step_handler(msg, lambda m: (delete_channel(m.text.strip()), bot.send_message(message.chat.id, "✅ O'chirildi.")))

@bot.message_handler(func=lambda m: m.text == "⭐ VIP Berish")
def ask_vip_user(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(message.chat.id, "VIP bermoqchi bo'lgan foydalanuvchi ID raqami va kunini yuboring:\n`User_ID | Kun`\nMasalan: `123456789 | 30`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_vip)

def process_vip(message):
    try:
        u_id, days = [i.strip() for i in message.text.split("|")]
        add_vip(int(u_id), int(days))
        bot.send_message(message.chat.id, f"✅ User {u_id} ga {days} kunlik VIP berildi!")
        bot.send_message(int(u_id), f"🎉 **Sizga {days} kunlik VIP obuna taqdim etildi!**")
    except:
        bot.send_message(message.chat.id, "❌ Noto'g'ri format!")

@bot.message_handler(func=lambda m: m.text == "✉️ Xabar yuborish (Rassilka)")
def ask_broadcast(message):
    if message.from_user.id != ADMIN_ID: return
    msg = bot.send_message(message.chat.id, "Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:")
    bot.register_next_step_handler(msg, start_broadcast)

def start_broadcast(message):
    users = get_users_list()
    success = 0
    status_msg = bot.send_message(message.chat.id, "⏳ Xabar yuborilmoqda...")
    for u_id in users:
        try:
            bot.copy_message(u_id, message.chat.id, message.message_id)
            success += 1
        except:
            pass
    bot.edit_message_text(f"✅ Xabar yuborish yakunlandi!\nYetib bordi: **{success}/{len(users)}** ta foydalanuvchiga.", message.chat.id, status_msg.message_id, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def handle_download(message):
    add_user(message.from_user.id)
    if not send_sub_menu(message.chat.id):
        return
    text = message.text.strip()
    
    if re.search(TIKTOK_PATTERN, text):
        status = bot.send_message(message.chat.id, "⏳ **TikTok video va musiqasi yuklanmoqda...**", parse_mode="Markdown")
        video_url, audio_url, title = download_tiktok(text)
        if video_url:
            bot.send_video(message.chat.id, video_url, caption="⚡️ **Video @TeezSaqlaBot orqali yuklandi!**", parse_mode="Markdown")
            if audio_url:
                try: bot.send_audio(message.chat.id, audio_url, caption=f"🎵 **Musiqa:** {title}")
                except: pass
            bot.delete_message(message.chat.id, status.message_id)
        else:
            bot.edit_message_text("❌ Videoni yuklab bo'lmadi.", message.chat.id, status.message_id)

    elif re.search(INSTAGRAM_PATTERN, text):
        status = bot.send_message(message.chat.id, "⏳ **Instagram video yuklanmoqda...**", parse_mode="Markdown")
        res_data, res_type = download_instagram(text)
        if res_type == "file":
            with open(res_data, 'rb') as video_file:
                bot.send_video(message.chat.id, video_file, caption="⚡️ **Video @TeezSaqlaBot orqali yuklandi!**", parse_mode="Markdown")
            if os.path.exists(res_data): os.remove(res_data)
            bot.delete_message(message.chat.id, status.message_id)
        elif res_type == "url":
            bot.send_video(message.chat.id, res_data, caption="⚡️ **Video @TeezSaqlaBot orqali yuklandi!**", parse_mode="Markdown")
            bot.delete_message(message.chat.id, status.message_id)
        else:
            bot.edit_message_text("❌ Videoni yuklab bo'lmadi.", message.chat.id, status.message_id)
    else:
        bot.send_message(message.chat.id, "⚠️ Iltimos, to'g'ri **TikTok** yoki **Instagram** havolasini yuboring!")

bot.polling(none_stop=True)
