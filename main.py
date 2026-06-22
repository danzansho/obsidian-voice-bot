import asyncio
import os
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.client.default import DefaultBotProperties  # <-- For auto-formatting
from aiogram.types import BotCommand  # <-- For Telegram Menu Button
from dotenv import load_dotenv
from groq import Groq

# Import database helpers
import database

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Telegram Bot with default Markdown formatting
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

# Define FSM states for user setup
class SetupStates(StatesGroup):
    waiting_for_path = State()

# Handler for /start command
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_data = await database.get_user_data(user_id)

    if user_data:
        await message.answer(
            f"Welcome back, *{message.from_user.first_name}*!\n\n"
            f"Your current Obsidian Inbox path is:\n`{user_data['path']}`\n\n"
            f"If you want to update it, please send the new absolute path now.\n\n"
            f"💡 *Tip:* You can check your usage statistics anytime by running /stats."
        )
    else:
        await message.answer(
            f"Hello, *{message.from_user.first_name}*!\n\n"
            f"I am your Obsidian assistant. To get started, I need to know where to save your notes.\n\n"
            f"Please send me the *absolute path* to your Obsidian `1 - Inbox` folder on your computer."
        )

    # Set the FSM state to wait for user input
    await state.set_state(SetupStates.waiting_for_path)

# Handler to capture the Obsidian path
# Handler to capture the Obsidian path with validation
@dp.message(SetupStates.waiting_for_path)
async def process_path(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    path = message.text.strip()

    # Normalize Windows backslashes to forward slashes
    normalized_path = path.replace("\\", "/")

    # VALIDATION: Check if the directory actually exists on this machine
    if not os.path.isdir(normalized_path):
        await message.answer(
            f"❌ *Invalid Path!*\n\n"
            f"The directory `{normalized_path}` does not exist on this machine.\n"
            f"Please make sure you created the folder, copied the path correctly, and try again."
        )
        # We do NOT clear the state here, so the bot keeps waiting for a valid path
        return

    # If path is valid, save to SQLite database asynchronously
    await database.save_user_path(user_id, normalized_path)

    await message.answer(
        f"✅ *Path saved successfully!*\n\n"
        f"Obsidian Inbox: `{normalized_path}`\n\n"
        f"You can now send me voice messages, and they will be saved directly to this folder.\n\n"
        f"📊 Use the /stats command to monitor your free note limits."
    )

    # Clear FSM state to return to normal mode
    await state.clear()

# Handler for /stats command
@dp.message(Command(commands=["stats"]))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    user_data = await database.get_user_data(user_id)

    if user_data:
        notes_count = user_data["notes_created"]
        limit = 30  # Free tier limit
        await message.answer(
            f"📊 *Your Obsidian Bot Stats:*\n\n"
            f"📂 *Vault Path:* `{user_data['path']}`\n"
            f"📝 *Notes captured:* `{notes_count} / {limit}` (Free tier)\n\n"
            f"ℹ️ *Note:* Upon reaching 30 notes, you will need to upgrade to Pro for unlimited access."
        )
    else:
        await message.answer("❌ You haven't set up your Obsidian path yet. Run /start first.")

# Handler for voice messages
@dp.message(F.voice)
async def handle_voice(message: types.Message, bot: Bot):
    user_id = message.from_user.id

    # Retrieve user data asynchronously
    user_data = await database.get_user_data(user_id)

    if not user_data:
        await message.answer("❌ I don't know where to save your notes. Please run /start to set your Obsidian path first.")
        return

    inbox_path = user_data["path"]
    notes_count = user_data["notes_created"]
    limit = 30  # Free tier limit

    # Paywall check
    if notes_count >= limit:
        await message.answer(
            "❌ *Limit Reached!*\n\n"
            "You have used all 30 free notes. "
            "Please upgrade to Pro by contacting the administrator to get unlimited access! 💰"
        )
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

        # Save note directly to Obsidian Inbox folder
        full_path = os.path.join(inbox_path, filename)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(final_note)

        # Increment counter in the database asynchronously
        await database.increment_notes_counter(user_id)

        new_count = notes_count + 1
        await msg.edit_text(
            f"✅ *Success! Note saved to Obsidian:*\n`{filename}`\n\n"
            f"📊 *Usage:* `{new_count} / {limit}` free notes used."
        )

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

    # Register bot commands programmatically in Telegram Menu Button (UX upgrade)
    await bot.set_my_commands([
        BotCommand(command="start", description="Set up or update your Obsidian path"),
        BotCommand(command="stats", description="Check your usage statistics")
    ])

    print("Database initialized. Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())