import logging
import json
import os
import shlex
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters as telegram_filters

script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, '.env'))

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

FILTERS_FILE = 'filters.json'

def load_filters():
    if os.path.exists(FILTERS_FILE):
        try:
            with open(FILTERS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_filters(filters_data):
    with open(FILTERS_FILE, 'w') as f:
        json.dump(filters_data, f, indent=4)

# Load filters into memory
chat_filters = load_filters()

def make_filter_entry_from_message(msg, fallback_text=None):
    if fallback_text:
        return {"type": "text", "data": fallback_text}
    if msg.text:
        return {"type": "text", "data": msg.text}
    if msg.photo:
        return {"type": "photo", "data": msg.photo[-1].file_id}
    if msg.sticker:
        return {"type": "sticker", "data": msg.sticker.file_id}
    if msg.video:
        return {"type": "video", "data": msg.video.file_id}
    if msg.animation:
        return {"type": "animation", "data": msg.animation.file_id}
    if msg.document:
        return {"type": "document", "data": msg.document.file_id}
    if msg.voice:
        return {"type": "voice", "data": msg.voice.file_id}
    if msg.audio:
        return {"type": "audio", "data": msg.audio.file_id}
    return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get bot information
    bot = await context.bot.get_me()
    
    # Create inline keyboard with "Add to Group" button
    keyboard = [
        [InlineKeyboardButton("Add to Group", url=f"https://t.me/{bot.username}?startgroup=true")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Prepare the welcome message
    welcome_message = (
        f"{bot.first_name} - Filter Bot\n\n"
        "Make your chat more lively with filters! The bot will reply to certain words or phrases you set up.\n\n"
        "Features:\n"
        "• Filters are case insensitive\n"
        "• Works with text, photos, stickers, videos, and more\n"
        "• Easy to set up custom triggers and responses\n\n"
        "Available Commands:\n"
        "• /filter &lt;trigger&gt; &lt;reply&gt; - Add a new filter. Every time someone says \"trigger\", the bot will reply with \"reply\". For multiple word filters, quote the trigger.\n"
        "• /filters - List all active filters in this chat.\n"
        "• /stop &lt;trigger&gt; - Remove a specific filter.\n"
        "• /stopall - Remove ALL filters in the current chat (cannot be undone).\n\n"
        "Simply set up triggers that the bot will respond to whenever someone uses them in chat!\n\n"
        "Official Bot Info:\n"
        "• Created by: @Titanic_bots\n"
        "• Owner: @hacker_unity_212 (shishimanu)"
    )
    
    # Send message with bot profile picture and buttons
    try:
        # Attempt to get bot's profile picture
        bot_photos = await context.bot.get_user_profile_photos(bot.id, limit=1)
        if bot_photos.photos and len(bot_photos.photos) > 0:
            # Send photo with caption
            await context.bot.send_photo(
                chat_id=update.effective_message.chat_id,
                photo=bot_photos.photos[0][0].file_id,
                caption=welcome_message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            # If no profile picture, send text message with buttons
            await update.message.reply_text(
                welcome_message,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
    except Exception as e:
        # Fallback to text message if there are any issues
        await update.message.reply_text(
            welcome_message,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    text = update.message.text
    try:
        parts = shlex.split(text)
    except ValueError as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Error parsing arguments: {e}"
        )
        return
    if len(parts) < 2:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "Usage: /filter &lt;trigger&gt; &lt;reply&gt;\n"
                "For multiple word filters, quote the trigger.\n"
                "Or reply to a message with: /filter &lt;trigger&gt;"
            )
        )
        return
    trigger = parts[1].lower()
    reply = " ".join(parts[2:]) if len(parts) >= 3 else None
    if chat_id not in chat_filters:
        chat_filters[chat_id] = {}
    entry = None
    if update.message.reply_to_message:
        entry = make_filter_entry_from_message(update.message.reply_to_message, reply)
    else:
        if reply is None:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Please provide a reply text, or reply to a message to use it as the filter response."
            )
            return
        entry = {"type": "text", "data": reply}
    if entry is None:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Unsupported message type for filter reply."
        )
        return
    chat_filters[chat_id][trigger] = entry
    save_filters(chat_filters)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Filter saved: '{trigger}'"
    )

async def list_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if chat_id not in chat_filters or not chat_filters[chat_id]:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No filters set in this chat."
        )
        return
    message = "Filters in this chat:\n"
    for trigger, val in chat_filters[chat_id].items():
        t = "text"
        if isinstance(val, dict):
            t = val.get("type", "text")
        message += f"- {trigger} ({t})\n"
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message
    )

async def stop_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    text = update.message.text
    
    try:
        parts = shlex.split(text)
    except ValueError as e:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Error parsing arguments: {e}"
        )
        return

    if len(parts) < 2:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Usage: /stop &lt;trigger&gt;"
        )
        return

    trigger = parts[1].lower()

    if chat_id in chat_filters and trigger in chat_filters[chat_id]:
        del chat_filters[chat_id][trigger]
        save_filters(chat_filters)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Filter stopped: '{trigger}'"
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Filter not found: '{trigger}'"
        )

async def stop_all_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if chat_id in chat_filters:
        chat_filters[chat_id] = {}
        save_filters(chat_filters)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="All filters stopped in this chat."
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="No filters to stop."
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not (update.message.text or update.message.caption):
        return
    chat_id = str(update.effective_chat.id)
    text = (update.message.text or update.message.caption or "").lower()
    if chat_id in chat_filters:
        for trigger, reply in chat_filters[chat_id].items():
            if trigger in text:
                if isinstance(reply, dict):
                    rtype = reply.get("type", "text")
                    data = reply.get("data", "")
                    if rtype == "text":
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=data
                        )
                    elif rtype == "photo":
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=data
                        )
                    elif rtype == "sticker":
                        await context.bot.send_sticker(
                            chat_id=update.effective_chat.id,
                            sticker=data
                        )
                    elif rtype == "video":
                        await context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=data
                        )
                    elif rtype == "animation":
                        await context.bot.send_animation(
                            chat_id=update.effective_chat.id,
                            animation=data
                        )
                    elif rtype == "document":
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=data
                        )
                    elif rtype == "voice":
                        await context.bot.send_voice(
                            chat_id=update.effective_chat.id,
                            voice=data
                        )
                    elif rtype == "audio":
                        await context.bot.send_audio(
                            chat_id=update.effective_chat.id,
                            audio=data
                        )
                    else:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=str(reply)
                        )
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=str(reply)
                    )
                return

if __name__ == '__main__':
    # You need to set your token here
    TOKEN = os.getenv("BOT_TOKEN")
    
    if not TOKEN or TOKEN == 'your_token_here':
        print("Error: BOT_TOKEN is not set correctly.")
        print("Please edit the .env file and replace 'your_token_here' with your actual Telegram bot token.")
        exit(1)

    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("filter", add_filter))
    application.add_handler(CommandHandler("filters", list_filters))
    application.add_handler(CommandHandler("stop", stop_filter))
    application.add_handler(CommandHandler("stopall", stop_all_filters))
    
    # Handle text messages that are not commands
    application.add_handler(MessageHandler(telegram_filters.TEXT & (~telegram_filters.COMMAND), handle_message))

    print("Bot is running...")
    application.run_polling()
