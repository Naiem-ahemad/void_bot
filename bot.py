from telegram import Update, InputFile , InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters ,CallbackQueryHandler
from chat.chat_engine import generate_response
from chat.chat_sessions import save_message
from mood.mood_detector import detect_mood
from images.generator import generate_image
import os , json
import emoji
import asyncio
import requests
from images.extractor import extract_text_from_image , clean_text_with_gemini
import uuid
from chat.intent_detector import detect_intent
import google.generativeai as genai
from config import GEMINI_API_KEY
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")
from chat.chat_sessions import list_chats , start_new_chat
from chat.chat_sessions import rename_chat_title , get_user_folder
from chat.chat_sessions import list_chats, get_user_folder
from chat.chat_sessions import find_session_by_title
from chat.searcher import web_search
from chat.summary import summarize_search_results
user_sessions = {}  # Make sure this is defined globally in bot.py if not already
concurrency_semaphore = asyncio.Semaphore(10)
TERABOX_API = "https://teraboxx.vercel.app/api?url="

async def expand_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text(
            "❗ Please provide a TeraBox link to expand.\n\nExample:\n`/expand https://terabox.com/s/xyz...`",
            parse_mode="Markdown"
        )

    short_url = context.args[0].strip()

    # Show typing action and loading message
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    loading_msg = await update.message.reply_text("⏳ Expanding your TeraBox link...")

    try:
        # Get data from API
        response = requests.get(TERABOX_API + short_url, timeout=15)
        response.raise_for_status()
        data = response.json()

        # Handle API failure
        if data.get("status") != "success" or not data.get("Extracted Info"):
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)
            return await update.message.reply_text("❌ Could not expand link or no downloadable files found.")

        # Delete loading message for smooth Telegram UI
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)

        # Format message
        lines = []
        buttons = []

        for item in data["Extracted Info"]:
            title = item.get("Title", "Untitled File")
            size = item.get("Size", "Unknown Size")
            dl_link = item.get("Direct Download Link")
            lines.append(f"*🎬{title}*\n\n📦 Size: `{size}`")
            buttons.append([InlineKeyboardButton("📥 Download", url=dl_link)])
        reply_markup = InlineKeyboardMarkup(buttons)

        # Send final message
        await update.message.reply_text(
            "\n\n".join(lines),
            parse_mode="Markdown",
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
    except Exception as e:
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)
        await update.message.reply_text(f"❌ Error expanding link:\n`{e}`", parse_mode="Markdown")

async def resume_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Get title from user argument (like /resume Naiem's Name)
    if not context.args:
        await update.message.reply_text("❌ Please provide a chat title. Usage: /resume <chat_title>")
        return

    title = " ".join(context.args).strip()

    session_id = find_session_by_title(user_id, title)
    if session_id:
        context.user_data["session_id"] = session_id  # 🔥 this is what your bot uses
        await update.message.reply_text(f"✅ Resumed your chat: {title}")
    else:
        await update.message.reply_text(f"❌ No chat found with title: {title}")

async def handle_new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    session_id = start_new_chat(user_id)

    # Store this session in user_data
    context.user_data["session_id"] = session_id
    await update.message.reply_text(f"✅ New chat started!\nSession ID: `{session_id}`", parse_mode="Markdown")

def extract_emojis(text: str) -> list:
    """Extracts emojis from a string"""
    return [char for char in text if char in emoji.EMOJI_DATA]
# chat/emoji_detector.py
def detect_emoji_response(text: str) -> str | None:
    emojis = extract_emojis(text)
    if not emojis:
        return None

    prompt = (
        f"The user sent these emojis: {' '.join(emojis)}.\n"
        f"Reply with exactly ONE emoji that best expresses a creative, meaningful or playful reaction."
    )

    try:
        response = gemini_model.generate_content(prompt)
        # Filter response to include only valid emojis
        emoji_response = ''.join([char for char in response.text if char in emoji.EMOJI_DATA])
        return emoji_response[0] if emoji_response else None  # only return one emoji
    except Exception:
        return None

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! I'm your smart AI bot 🤖\nJust send a message")

from telegram.constants import ChatAction
import os
from telegram import InputFile
import asyncio

def rename_chat_title(user_id, session_id, new_title):
    path = os.path.join(get_user_folder(user_id), session_id)
    if not os.path.exists(path):
        return False

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data["title"] = new_title

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return True

async def handle_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    sessions = list_chats(user_id)

    if not sessions:
        await update.message.reply_text("❌ No previous chats found.")
        return

    msg = "🗂️ Your previous chats:\n\n"
    for i, chat in enumerate(sessions, 1):
        msg += f"{i}. {chat['title']} — ID: `{chat['id']}`\n"

    await update.message.reply_text(msg, parse_mode="Markdown")
async def handle_user_logic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_msg = update.message.text
    user_id = update.message.from_user.id

    emoji_reply = detect_emoji_response(user_msg)
    if emoji_reply:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(10)
        await update.message.reply_text(emoji_reply)
        return

    intent = detect_intent(user_msg)
    if intent == "image":
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        loading_msg = await update.message.reply_text("⏳ Generating image...")
        try:
            img_path = generate_image(user_msg)
            img_path = os.path.abspath(img_path)
            if not os.path.exists(img_path):
                await update.message.reply_text("❌ Image file not found.")
                return
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
            with open(img_path, 'rb') as photo:
                await update.message.reply_photo(photo=InputFile(photo), caption=f"🎨 Generated for: '{user_msg}'")
        except Exception as e:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)
            await update.message.reply_text(f"❌ Failed to generate image: {e}")
        return

    if intent == "search":
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        loading_msg = await update.message.reply_text("🔍 Searching...")
        try:
            raw_results = web_search(user_msg)
            summary = summarize_search_results(raw_results)
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)
            await update.message.reply_text(f"📄 Summary:\n\n{summary}")
        except Exception as e:
            await update.message.reply_text(f"❌ Search failed: {e}")
        return

    if intent == "chat":
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await asyncio.sleep(min(len(user_msg) * 0.03, 3))
        mood = detect_mood(user_msg)
        session_id = context.user_data.get("session_id")
        if not session_id:
            session_id = start_new_chat(user_id)
            context.user_data["session_id"] = session_id
        from chat.chat_engine import load_memory_summary
        memory = load_memory_summary(user_id, session_id)
        reply = generate_response(user_msg, user_id, session_id, memory=memory)
        save_message(user_id, session_id, user_msg, reply)
        await update.message.reply_text(f"{reply}\n\n🧠 Detected Mood: {mood}")
        return
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async def limited_user_handler():
        async with concurrency_semaphore:
            await handle_user_logic(update, context)

    asyncio.create_task(limited_user_handler())

# Handle photo uploads for OCR
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. Show "Extracting..." loader
    loading_msg = await update.message.reply_text("⏳ Extracting...")

    try:
        # 2. Download image
        photo_file = await update.message.photo[-1].get_file()
        filename = f"{uuid.uuid4()}.jpg"
        file_path = os.path.join("images/downloads", filename)
        await photo_file.download_to_drive(file_path)

        # 3. Extract and clean text
        raw_text = extract_text_from_image(file_path)
        clean_text = clean_text_with_gemini(raw_text)

        # 4. Delete "Extracting..." message
        await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)

        # 5. Add copy button
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 Copy Text", callback_data="copy_text")]
        ])

        # 6. Send final cleaned text with button
        sent_msg = await update.message.reply_text(
            f"📝 Extracted & Cleaned Text:\n\n<code>{clean_text}</code>",
            reply_markup=keyboard,
            parse_mode="HTML"
        )

        context.user_data["last_extracted_text"] = clean_text
        context.user_data["copy_message_id"] = sent_msg.message_id
        # Optional: Save clean text to context for later copy
        context.user_data["last_extracted_text"] = clean_text
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to process image: {e}")
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("✅ Ready to copy!", show_alert=False)

    if query.data == "copy_text":
        text = context.user_data.get("last_extracted_text", "❌ Nothing to copy.")
        message_id = context.user_data.get("copy_message_id", None)

        if message_id:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=message_id,
                text=f"✅ Click to Copy:\n\n<code>{text}</code>",
                parse_mode="HTML"
            )
def main():
    from config import BOT_TOKEN
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CommandHandler("chats", handle_chats))
    app.add_handler(CommandHandler("newchat", handle_new_chat))
    app.add_handler(CommandHandler("resume", resume_chat))
    app.add_handler(CommandHandler("expand", expand_link))
    print("✅ Bot is running...")
    app.run_polling()
if __name__ == "__main__":
    main()
