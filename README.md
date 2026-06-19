# Obsidian Voice-to-Zettelkasten Bot 🎙🤖

A lightweight Telegram bot written in Python that instantly captures your voice notes, transcribes them using AI, formats them into structured Zettelkasten notes, and saves them directly into your local Obsidian vault.

This project solves the issue of slow mobile Obsidian app loading times by allowing frictionless, zero-delay voice capture on the go.

## How It Works
1. You record a quick voice message in Telegram.
2. The bot downloads the audio and transcribes it using Whisper (via Groq API).
3. The raw transcript is passed to LLaMA 3.3 to generate tags, a summary, and format it.
4. The bot saves a .md file directly into your Obsidian Inbox folder.

## Prerequisites
- Python 3.11+
- A Telegram Bot Token (from @BotFather)
- A Groq API Key (free from console.groq.com)
- A local Obsidian vault

## Installation & Setup

1. Clone the repository:
git clone https://github.com/danzansho/obsidian-voice-bot.git
cd obsidian-voice-bot

2. Create and activate a virtual environment:
python -m venv venv
source venv/Scripts/activate  # On Windows Git Bash

3. Install dependencies:
pip install aiogram python-dotenv groq

4. Configure environment variables:
Create a .env file in the root folder and add the following:
BOT_TOKEN=your_telegram_bot_token
GROQ_API_KEY=your_groq_api_key
INBOX_PATH=C:/Path/To/Your/Obsidian/Vault/1 - Inbox

(Note: Use forward slashes / in INBOX_PATH even on Windows to prevent path escaping issues).

## Usage

Run the bot locally:
python main.py

Now, go to Telegram, open your bot, and send a voice message. Within seconds, a new formatted .md file will magically appear in your Obsidian Inbox folder.

## Note Template Output
The generated note will look like this:

# [AI-Generated Title]
#inbox #idea #topic

Brief summary of your stream of thoughts.

### 🎙 Сырой транскрипт:
[Exact literal transcription of your voice]