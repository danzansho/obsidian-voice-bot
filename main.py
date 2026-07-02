import asyncio
import os
import re
import uuid
import datetime
import logging
import urllib.parse
from html import escape as html_escape
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import StatesGroup, State      
from aiogram.fsm.context import FSMContext            
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import BotCommand, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from groq import Groq

import database

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler("bot.log", maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ---------- Config ----------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
REDIRECT_BASE_URL = os.getenv("REDIRECT_BASE_URL")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is not set")
if not REDIRECT_BASE_URL:
    logging.warning("REDIRECT_BASE_URL is not set in .env. Quick Add button will be disabled.")
if not ADMIN_ID:
    logging.warning("ADMIN_ID is not set in .env. Support tickets will be disabled.")

NOTES_LIMIT = 10
MAX_VOICE_SECONDS = 15 * 60
MAX_URI_CONTENT_LENGTH = 1200

# We use HTML parse mode globally
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)


# ---------- States ----------
class SupportStates(StatesGroup):
    waiting_for_support = State()


# ---------- Helpers ----------
def sanitize_filename(raw: str, fallback: str) -> str:
    if not raw:
        return fallback
    cleaned = re.sub(r"[^\w\s\-]", "", raw, flags=re.UNICODE)
    cleaned = re.sub(r"\s+", "_", cleaned).strip("_")
    if not cleaned:
        return fallback
    return cleaned[:60]


def build_redirect_uri(base_url: str, clean_title: str, content: str) -> str | None:
    encoded_title = urllib.parse.quote(clean_title, safe="")
    encoded_content = urllib.parse.quote(content, safe="")
    uri = f"{base_url}/open?name={encoded_title}&content={encoded_content}"
    if len(uri) < 8000:
        return uri
    return None


def wrap_in_code_block(text: str) -> str:
    escaped = html_escape(text)
    return f"<pre><code>{escaped}</code></pre>"


def safe_truncate_text(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "\n\n... (truncated)"


# ---------- Handlers ----------
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    logging.info(f"User {user_id} triggered /start")
    await database.register_user(user_id)

    safe_name = html_escape(message.from_user.first_name or "Friend")

    await message.answer(
        f"Hello, <b>{safe_name}</b>!\n\n"
        f"I am your Obsidian Zettelkasten assistant.\n"
        f"Send me a voice message, and I will transform it into a clean <code>.md</code> note.\n\n"
        f"💡 <b>/set_vault</b> [name] — required if you want the Quick Add button to work.\n"
        f"💡 <b>/support</b> — contact the developer / report bugs.\n"
        f"💡 <b>/stats</b> — check your usage."
    )


@dp.message(Command(commands=["set_vault"]))
async def cmd_set_vault(message: types.Message):
    user_id = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("❌ Please specify your vault name: /set_vault MyNotes")
        return

    vault_name = args[1].strip()
    if not vault_name:
        await message.answer("❌ Vault name cannot be empty.")
        return

    await database.set_user_vault(user_id, vault_name)
    safe_vault = html_escape(vault_name)
    await message.answer(f"✅ Vault successfully set as: <b>{safe_vault}</b>")


@dp.message(Command(commands=["stats"]))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    user_data = await database.get_user_data(user_id)

    if user_data:
        notes_count = user_data["notes_created"]
        vault = user_data.get("vault_name") or "not set"
        safe_vault = html_escape(vault)
        await message.answer(
            f"📊 <b>Your Obsidian Bot Stats:</b>\n\n"
            f"📝 <b>Notes generated:</b> <code>{notes_count} / {NOTES_LIMIT}</code>\n"
            f"🗄 <b>Vault:</b> <code>{safe_vault}</code>\n\n"
            f"ℹ️ <i>After reaching the limit, please upgrade to Pro.</i>"
        )
    else:
        await message.answer("Please run /start first.")


@dp.message(Command(commands=["support"]))
async def cmd_support(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logging.info(f"User {user_id} triggered /support")
    await message.answer(
        "📝 Please send your message, bug report, or feature request.\n"
        "I will forward it directly to the developer."
    )
    await state.set_state(SupportStates.waiting_for_support)


@dp.message(SupportStates.waiting_for_support)
async def process_support(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    admin_id = os.getenv("ADMIN_ID")

    if not admin_id:
        await message.answer("❌ Support is temporarily unavailable. Please try again later.")
        await state.clear()
        return

    support_text = message.text.strip() if message.text else ""
    if not support_text:
        await message.answer("❌ Message cannot be empty. Please write something.")
        return

    user_name = html_escape(message.from_user.full_name or "Unknown")
    username = f"@{message.from_user.username}" if message.from_user.username else "No username"

    ticket_payload = (
        f"🚨 <b>New Support Ticket</b>\n\n"
        f"👤 <b>From:</b> {user_name} ({username}, ID: <code>{user_id}</code>)\n\n"
        f"💬 <b>Message:</b>\n<i>{html_escape(support_text)}</i>"
    )

    try:
        await bot.send_message(chat_id=int(admin_id), text=ticket_payload)
        await message.answer("✅ Your message has been sent to the developer! Thank you for your feedback.")
    except Exception as e:
        logging.error(f"Failed to forward support message from {user_id} to admin: {e}")
        await message.answer("❌ Failed to deliver message. Please try again later.")

    await state.clear()


@dp.message(F.voice)
async def handle_voice(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    msg = None

    await database.register_user(user_id)
    user_data = await database.get_user_data(user_id)
    vault_name = user_data.get("vault_name") if user_data else None

    if not vault_name:
        await message.answer(
            "⚠️ You have not set your vault name yet. Use /set_vault so the Quick Add link can work."
        )

    duration = message.voice.duration or 0
    if duration > MAX_VOICE_SECONDS:
        await message.answer(f"❌ Voice message is too long (max {MAX_VOICE_SECONDS // 60} min).")
        return

    # Atomic counter increment
    reserved = await database.try_increment_notes_counter(user_id, NOTES_LIMIT)
    if not reserved:
        await message.answer(
            "❌ <b>Limit reached!</b> Upgrade to Pro to capture more notes."
        )
        return

    current_usage = user_data["notes_created"] + 1 if user_data else 1
    msg = await message.answer("⏳ Processing your thought...")

    unique = uuid.uuid4().hex
    audio_dest = f"temp_voice_{user_id}_{unique}.ogg"
    md_dest = f"temp_note_{user_id}_{unique}.md"

    try:
        # --- 1. Download voice ---
        file_id = message.voice.file_id
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, audio_dest)

        # --- 2. Transcribe via Groq ---
        try:
            with open(audio_dest, "rb") as audio_file:
                transcription = groq_client.audio.transcriptions.create(
                    file=(audio_dest, audio_file.read()),
                    model="whisper-large-v3",
                )
            raw_text = transcription.text.strip() if transcription and transcription.text else ""
        except Exception as e:
            logging.error(f"Groq transcription error for user {user_id}: {e}", exc_info=True)
            await database.decrement_notes_counter(user_id)
            await msg.edit_text("❌ <b>Transcription failed.</b>\nGroq returned an error. Try again later.")
            return

        if not raw_text:
            logging.warning(f"User {user_id}: empty transcription")
            await database.decrement_notes_counter(user_id)
            await msg.edit_text("❌ Could not understand audio. Try speaking more clearly.")
            return

        # --- 3. Generate note ---
        prompt = f'''
You are an Obsidian Zettelkasten assistant.

Transcribed text:
---
{raw_text}
---

Detect the language of the text and write the entire note in that language.

Output EXACTLY this structure and nothing else:
- Do NOT wrap output in triple backticks (```).
- Do NOT add a YAML frontmatter block (---).
- Start immediately with the title.

# [Concise 2-5 word title that reflects the MAIN TOPIC, in the same language as the transcript]

**Summary:**
- [Clear, useful bullet-point summary. Remove filler words, hesitations and repetitions]

***
**🎙️ Raw Transcript:**
> [Insert the exact original transcribed text here, unchanged]
'''

        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama-3.3-70b-versatile",
            )
            llama_content = chat_completion.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Groq chat completion error for user {user_id}: {e}", exc_info=True)
            await database.decrement_notes_counter(user_id)
            await msg.edit_text("❌ <b>AI formatting failed.</b>\nGroq returned an error. Try again.")
            return

        if not llama_content:
            logging.warning(f"User {user_id}: empty LLM output")
            await database.decrement_notes_counter(user_id)
            await msg.edit_text("❌ The AI returned an empty response. Please try again.")
            return

        # --- 4. Build title & filename ---
        title_line = llama_content.split("\n")[0]
        raw_title = title_line.lstrip("#").strip()
        fallback_title = f"Idea_{datetime.datetime.now().strftime('%H-%M-%S')}"
        clean_title = sanitize_filename(raw_title, fallback_title)
        final_filename = f"{clean_title}.md"

        now = datetime.datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        time_str = now.strftime("%H:%M")
        yaml_title = clean_title.replace("_", " ")

        yaml_frontmatter = (
            f"---\ntitle: {yaml_title}\ndate: {date_str}\ntime: {time_str}\n"
            f"tags: [inbox, idea, voice]\n---\n\n"
        )

        final_note = yaml_frontmatter + llama_content

        # --- 5. Write .md ---
        with open(md_dest, "w", encoding="utf-8") as f:
            f.write(final_note)

        # --- 6. Send formatted note text as a copy-on-tap block ---
        note_for_telegram = safe_truncate_text(final_note, 3400)
        code_block = wrap_in_code_block(note_for_telegram)

        await message.answer(code_block)

        if len(final_note) > 3400:
            await message.answer(
                "⚠️ <i>Note was truncated above. The full version is in the .md file.</i>"
            )

        # --- 7. Build Redirect URI ---
        short_for_uri = final_note[:MAX_URI_CONTENT_LENGTH]
        redirect_uri = None
        if REDIRECT_BASE_URL and vault_name:
            redirect_uri = build_redirect_uri(REDIRECT_BASE_URL, clean_title, short_for_uri)

        document = FSInputFile(md_dest, filename=final_filename)
        safe_vault = html_escape(vault_name or "not set")

        # Telegram perfectly allows our redirection link because it is standard HTTPS
        if redirect_uri:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📥 Quick Add to Obsidian", url=redirect_uri)]
            ])
            caption = (
                f"✅ <b>Done!</b>\n"
                f"Tap the button below to add the note directly into vault: <code>{safe_vault}</code>.\n"
                f"📊 {current_usage}/{NOTES_LIMIT}"
            )
        else:
            keyboard = None
            caption = (
                f"✅ <b>Done!</b>\n\n"
                f"⚡ Tap the code block above to copy and paste into Obsidian.\n"
                f"📁 The full .md file is attached.\n"
                f"📊 {current_usage}/{NOTES_LIMIT}"
            )

        await message.answer_document(
            document=document,
            caption=caption,
            reply_markup=keyboard
        )

        try:
            await msg.delete()
        except TelegramBadRequest:
            pass

    except Exception as e:
        logging.error(f"Unexpected error in handle_voice for user {user_id}: {e}", exc_info=True)
        await database.decrement_notes_counter(user_id)
        if msg:
            try:
                await msg.edit_text("❌ Failed to process audio. Please try again.")
            except TelegramBadRequest:
                pass

    finally:
        if os.path.exists(audio_dest):
            os.remove(audio_dest)
        if os.path.exists(md_dest):
            os.remove(md_dest)


async def main():
    await database.init_db()
    await bot.set_my_commands([
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="set_vault", description="Set your Obsidian vault name"),
        BotCommand(command="support", description="Contact developer / report bugs"),
        BotCommand(command="stats", description="Check limits and vault")
    ])
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
