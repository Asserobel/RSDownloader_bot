import os
import re
import yt_dlp
import requests
import uuid
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler, filters

# === CHARGEMENT VARIABLES ENV ===
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DOWNLOAD_DIR = "downloads"
URL_STORAGE = {}  # Pour stocker les URL avec identifiants courts

# === FONCTION POUR ENVOYER INFOS DE LA VIDÉO ===
async def send_video_info(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    try:
        uid = str(uuid.uuid4())
        URL_STORAGE[uid] = url

        ydl_opts = {
            'quiet': True,
            'noplaylist': True,
            'http_headers': {'User-Agent': 'Mozilla/5.0'},
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Sans titre')
            duration = int(info.get('duration') or 0)
            views = info.get('view_count', 'N/A')
            thumbnail = info.get('thumbnail')
            minutes, seconds = divmod(duration, 60)
            formatted_duration = f"{minutes} min {seconds} sec"

            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("📅 Télécharger (SD)", callback_data=f"download_sd|{uid}")]
            ])

            await update.message.reply_photo(
                photo=thumbnail,
                caption=f"🎨 <b>{title}</b>\n🕒 {formatted_duration}\n👁️ {views} vues",
                parse_mode='HTML',
                reply_markup=reply_markup
            )

    except Exception as e:
        await update.message.reply_text(f"🚨 Erreur : {e}")

# === TELECHARGER FORMAT SD ===
async def download_sd_video(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str, query):
    path = os.path.join(DOWNLOAD_DIR, f"{uuid.uuid4()}.mp4")
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    # Envoyer un nouveau message texte au lieu d'éditer la photo
    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="🔄 Téléchargement de la vidéo SD..."
    )

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
        'outtmpl': path,
        'quiet': True,
        'merge_output_format': 'mp4',
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4',
        }],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        await msg.edit_text("✅ Téléchargement terminé. Envoi de la vidéo...")
        await context.bot.send_video(chat_id=update.effective_chat.id, video=open(path, 'rb'))
        os.remove(path)
    except Exception as e:
        await msg.edit_text(f"🚨 Erreur : {e}")

# === BOUTON HANDLER ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if not data or "|" not in data:
        await query.edit_message_text("❌ Donnée invalide.")
        return

    action, uid = data.split("|")
    url = URL_STORAGE.get(uid)

    if not url:
        await query.edit_message_text("❌ Lien expiré ou invalide.")
        return

    if action == "download_sd":
        await download_sd_video(update, context, url, query)

# === START + MESSAGE HANDLER ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Envoie-moi un lien Facebook, YouTube, Instagram, TikTok ou Douyin.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = extract_url(update.message.text)
    if url:
        await send_video_info(update, context, url)
    else:
        await update.message.reply_text("❌ Aucun lien valide détecté.")

# === EXTRACTION DE LIEN ===
def extract_url(text):
    pattern = r'(https?://[\w./?=&%-]+)'
    match = re.search(pattern, text)
    return match.group(0) if match else None

# === MAIN ===
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🤖 Bot prêt !")
    app.run_polling()

if __name__ == "__main__":
    main()
