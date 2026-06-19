import asyncio
import os
import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from dotenv import load_dotenv
from groq import Groq

# 1. Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
INBOX_PATH = os.getenv("INBOX_PATH")

# 2. Initialize Telegram Bot and Groq Client
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Hello! I am your Obsidian Zettelkasten assistant. Send me a voice message to capture your thoughts.")

@dp.message(F.voice)
async def handle_voice(message: types.Message, bot: Bot):
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

        Do the following:
        1. Create a short, catchy title (in Russian).
        2. Write 2-3 tags (e.g., #inbox, #мысль) (in Russian).
        3. Make a brief summary (1-2 sentences in Russian).
        4. Print the header "### 🎙 Сырой транскрипт:" and output the EXACT literal transcript of my voice without any edits or formatting.

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
        full_path = os.path.join(INBOX_PATH, filename)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(final_note)

        await msg.edit_text(f"✅ Success! Note saved to Obsidian:\n`{filename}`")

    except Exception as e:
        await msg.edit_text(f"❌ Error occurred: {e}")

    finally:
        # Cleanup temporary audio file
        if os.path.exists(destination):
            os.remove(destination)

async def main():
    print("Bot is running. Waiting for voice messages...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())