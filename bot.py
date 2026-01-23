import logging
import json
import os
import shlex
from dotenv import load_dotenv
from telegram import Update
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
    await update.message.reply_text(
        "Make your chat more lively with filters; The bot will reply to certain words!\n\n"
        "Filters are case insensitive; every time someone says your trigger words, Rose will reply something else! can be used to create your own commands, if desired.\n\n"
        "Commands :\n"
        "- /filter <trigger> <reply>: Every time someone says \"trigger\", the bot will reply with \"sentence\". For multiple word filters, quote the trigger.\n"
        "- /filters: List all chat filters.\n"
        "- /stop <trigger>: Stop the bot from replying to \"trigger\".\n"
        "- /stopall: Stop ALL  filters in the current chat. This cannot be undone."
    )

async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    text = update.message.text
    try:
        parts = shlex.split(text)
    except ValueError as e:
        await update.message.reply_text(f"Error parsing arguments: {e}")
        return
    if len(parts) < 2:
        await update.message.reply_text(
            "Usage: /filter <trigger> <reply>\n"
            "For multiple word filters, quote the trigger.\n"
            "Or reply to a message with: /filter <trigger>"
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
            await update.message.reply_text("Please provide a reply text, or reply to a message to use it as the filter response.")
            return
        entry = {"type": "text", "data": reply}
    if entry is None:
        await update.message.reply_text("Unsupported message type for filter reply.")
        return
    chat_filters[chat_id][trigger] = entry
    save_filters(chat_filters)
    await update.message.reply_text(f"Filter saved: '{trigger}'")

async def list_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    if chat_id not in chat_filters or not chat_filters[chat_id]:
        await update.message.reply_text("No filters set in this chat.")
        return
    message = "Filters in this chat:\n"
    for trigger, val in chat_filters[chat_id].items():
        t = "text"
        if isinstance(val, dict):
            t = val.get("type", "text")
        message += f"- {trigger} ({t})\n"
    await update.message.reply_text(message)

async def stop_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    text = update.message.text
    
    try:
        parts = shlex.split(text)
    except ValueError as e:
        await update.message.reply_text(f"Error parsing arguments: {e}")
        return

    if len(parts) < 2:
        await update.message.reply_text("Usage: /stop <trigger>")
        return

    trigger = parts[1].lower()

    if chat_id in chat_filters and trigger in chat_filters[chat_id]:
        del chat_filters[chat_id][trigger]
        save_filters(chat_filters)
        await update.message.reply_text(f"Filter stopped: '{trigger}'")
    else:
        await update.message.reply_text(f"Filter not found: '{trigger}'")

async def stop_all_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    
    if chat_id in chat_filters:
        chat_filters[chat_id] = {}
        save_filters(chat_filters)
        await update.message.reply_text("All filters stopped in this chat.")
    else:
        await update.message.reply_text("No filters to stop.")

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
                            text=data,
                            reply_to_message_id=update.message.message_id
                        )
                    elif rtype == "photo":
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=data,
                            reply_to_message_id=update.message.message_id
                        )
                    elif rtype == "sticker":
                        await context.bot.send_sticker(
                            chat_id=update.effective_chat.id,
                            sticker=data,
                            reply_to_message_id=update.message.message_id
                        )
                    elif rtype == "video":
                        await context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=data,
                            reply_to_message_id=update.message.message_id
                        )
                    elif rtype == "animation":
                        await context.bot.send_animation(
                            chat_id=update.effective_chat.id,
                            animation=data,
                            reply_to_message_id=update.message.message_id
                        )
                    elif rtype == "document":
                        await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=data,
                            reply_to_message_id=update.message.message_id
                        )
                    elif rtype == "voice":
                        await context.bot.send_voice(
                            chat_id=update.effective_chat.id,
                            voice=data,
                            reply_to_message_id=update.message.message_id
                        )
                    elif rtype == "audio":
                        await context.bot.send_audio(
                            chat_id=update.effective_chat.id,
                            audio=data,
                            reply_to_message_id=update.message.message_id
                        )
                    else:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=str(reply),
                            reply_to_message_id=update.message.message_id
                        )
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=str(reply),
                        reply_to_message_id=update.message.message_id
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
