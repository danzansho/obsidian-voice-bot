import asyncio
import os
import datetime # <-- Добавили для времени
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from dotenv import load_dotenv
from groq import Groq

# 1. Загружаем ключи и пути
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
INBOX_PATH = os.getenv("INBOX_PATH") # <-- Подтянули путь к Обсидиану

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
groq_client = Groq(api_key=GROQ_API_KEY)

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer("Здарова. Готов закидывать мысли прямо в твой Obsidian.")

@dp.message(F.voice)
async def handle_voice(message: types.Message, bot: Bot):
    msg = await message.answer("⏳ Скачиваю аудио...")
    destination = "temp_voice.ogg"

    try:
        # Скачиваем
        file_id = message.voice.file_id
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, destination)

        # Расшифровываем
        await msg.edit_text("🎧 Слушаю и расшифровываю...")
        with open(destination, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
              file=(destination, audio_file.read()),
              model="whisper-large-v3",
            )
        raw_text = transcription.text

        # Генерируем заметку
        await msg.edit_text("🧠 Упаковываю по методу Лумана...")
        prompt = f"""
        Ты мой ассистент для базы знаний Obsidian.
        Вот мой сырой поток мыслей: "{raw_text}"

        Сделай следующее:
        1. Придумай короткий заголовок.
        2. Напиши 2-3 тега (например, #inbox, #мысль).
        3. Сделай краткую выжимку (1-2 предложения).
        4. Выведи заголовок "### 🎙 Сырой транскрипт:" и напиши точный дословный текст без изменений.

        Верни ответ строго в формате Markdown. Никаких приветствий, только сама заметка.
        """

        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        )
        final_note = chat_completion.choices[0].message.content

        # ==========================================
        # МАГИЯ: СОХРАНЯЕМ ФАЙЛ ПРЯМО В OBSIDIAN
        # ==========================================
        # Генерируем имя файла: Год-Месяц-День_Часы-Минуты-Секунды.md
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Idea_{current_time}.md"

        # Склеиваем путь к папке и имя файла
        full_path = os.path.join(INBOX_PATH, filename)

        # Записываем текст в файл (обязательно utf-8, чтобы русский язык не сломался)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(final_note)

        await msg.edit_text(f"✅ Готово! Заметка улетела в Obsidian:\n`{filename}`")

    except Exception as e:
        await msg.edit_text(f"❌ Ошибка: {e}")

    finally:
        # Убираем за собой аудиофайл
        if os.path.exists(destination):
            os.remove(destination)

async def main():
    print("Бот запущен! Жду голосовухи.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())