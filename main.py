import asyncio
import os
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
from groq import Groq

# Import our database helpers from database.py
import database

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Telegram Bot, Dispatcher, and Groq Client
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

# Define FSM states for user setup (System 2 thinking)
class SetupStates(StatesGroup):
    waiting_for_path = State()

# Handler for /start command
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    existing_path = await database.get_user_path(user_id)

    if existing_path:
        await message.answer(
            f"Welcome back, {message.from_user.first_name}!\n\n"
            f"Your current Obsidian Inbox path is:\n`{existing_path}`\n\n"
            f"If you want to update it, please send the new absolute path now."
        )
    else:
        await message.answer(
            f"Hello, {message.from_user.first_name}!\n\n"
            f"I am your Obsidian assistant. To get started, I need to know where to save your notes.\n\n"
            f"Please send me the **absolute path** to your Obsidian `1 - Inbox` folder on your computer."
        )

    # Set the FSM state to wait for user input
    await state.set_state(SetupStates.waiting_for_path)

# Handler to capture the Obsidian path (only triggered when waiting_for_path state is active)
@dp.message(SetupStates.waiting_for_path)
async def process_path(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    path = message.text.strip()

    # Simple validation: normalize Windows backslashes to forward slashes
    normalized_path = path.replace("\\", "/")

    # Save path to SQLite database asynchronously
    await database.save_user_path(user_id, normalized_path)

    await message.answer(
        f"✅ Path saved successfully!\n\n"
        f"Obsidian Inbox: `{normalized_path}`\n\n"
        f"You can now send me voice messages, and they will be saved directly to this folder."
    )

    # Clear FSM state to return to normal mode
    await state.clear()

# Handler for voice messages
@dp.message(F.voice)
async def handle_voice(message: types.Message, bot: Bot):
    user_id = message.from_user.id

    # Retrieve the user's specific path from the database
    inbox_path = await database.get_user_path(user_id)

    if not inbox_path:
        await message.answer("❌ I don't know where to save your notes. Please run /start to set your Obsidian path first.")
        return

    msg = await message.answer("⏳ Downloading audio...")
    destination = "temp_voice.ogg"

    try:
        # Download voice file from Telegram
        file_id = message.voice.file_id
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, destination)

        # Transcribe audio using Groq Whisper API
        await msg.edit_text("🎧 Transcribing audio...")
        with open(destination, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
              file=(destination, audio_file.read()),
              model="whisper-large-v3",
            )
        raw_text = transcription.text

        # Generate Zettelkasten note using LLaMA 3.3
        await msg.edit_text("🧠 Formatting Zettelkasten note...")
        prompt = f"""
        You are my Obsidian Zettelkasten assistant.
        I dictated a raw stream of thoughts: "{raw_text}"

        Detect the language of the dictated text and do the following strictly in that SAME language:
        1. Create a short, catchy title.
        2. Write 2-3 tags (e.g., #inbox, #idea).
        3. Make a brief summary (1-2 sentences).
        4. Print the header "### 🎙 Raw Transcript:" (translated to the detected language, e.g., "### 🎙 Сырой транскрипт:" for Russian) and output the EXACT literal transcript of my voice without any edits or formatting.

        Return the response strictly in Markdown format. No greetings, no extra text, just the note itself.
        """

        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )
        final_note = chat_completion.choices[0].message.content

        # Generate unique filename using timestamp
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Idea_{current_time}.md"

        # Save note directly to Obsidian Inbox folder retrieved from DB
        full_path = os.path.join(inbox_path, filename)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(final_note)

        await msg.edit_text(f"✅ Success! Note saved to Obsidian:\n`{filename}`")

    except Exception as e:
        await msg.edit_text(f"❌ Error occurred: {e}")

    finally:
        # Cleanup temporary audio file
        if os.path.exists(destination):
            os.remove(destination)

# Main entry point
async def main():
    # Initialize database tables asynchronously
    await database.init_db()
    print("Database initialized. Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())