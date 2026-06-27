# Obsidian Voice Zettelkasten Bot 🎙️🧠

An elegant, production-ready Telegram Bot designed to capture your raw voice thoughts on the go, transcribe them with high accuracy, and format them into perfectly structured Markdown notes for your Obsidian vault — with **zero friction**.

Developed with Python, aiogram 3.x, Groq API (Whisper-large-v3 + LLaMA 3.3 70B), FastAPI, and SQLite.

---

## The Problem we solve 🛑
Mobile capture in Obsidian is slow. Waiting for plugins to load, creating files manually, and typing on a small keyboard destroys the creative flow.

**Our Solution:**
1. Open Telegram, press record, ramble your thoughts.
2. The bot transcribes your voice (Whisper) and uses LLaMA 3.3 to structure the raw text into a clean Zettelkasten note with automatic titles, tags, and bullet-point summaries.
3. Tap the generated **Quick Add link** (which triggers a secure redirect to the `obsidian://` protocol) or download the `.md` file directly. Done.

---

## Features ✨
- ⚡ **Zero Friction Capture:** No heavy setup required. Type `/start` and start recording.
- 🧠 **AI-Powered Structuring:** LLaMA 3.3 automatically cleans up your stutters, extracts key ideas into bullet points, and generates semantic titles.
- 📂 **Auto-YAML Frontmatter:** Note is created with valid YAML metadata (`title`, `date`, `time`, `tags`) directly in Python to avoid layout bugs.
- 🔗 **Smart Deep-Linking:** Automatically generates `obsidian://` links for one-tap import into your local mobile or desktop vault via an HTTPS redirect bridge.
- 📋 **One-Tap Copy Block:** Text is duplicated in a special `<pre><code>` block for instant clipboard copy on mobile.
- 📬 **Feedback Loop:** Built-in `/support` ticketing system to forward user messages directly to the admin.
- 🛡️ **Production-Ready Core:** Features atomic database counters, rotating logs, async architecture (`aiosqlite` + `aiogram`), and full error recovery.

---

## Technical Architecture ⚙️
```
[User Voice] -> (Telegram Bot) -> [Whisper API] -> [LLaMA 3.3] -> [Python YAML Formatter] -> [FastAPI Redirect] -> [Obsidian Vault]
```

---

## Installation & Self-Hosting 🛠️

### Prerequisites
- Python 3.11+
- Groq API Key
- Telegram Bot Token (from @BotFather)

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/danzansho/obsidian-voice-bot.git
   cd obsidian-voice-bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the root folder:
   ```env
   BOT_TOKEN=your_telegram_bot_token
   GROQ_API_KEY=your_groq_api_key
   ADMIN_ID=your_telegram_user_id_for_support_tickets
   REDIRECT_BASE_URL=https://your-redirect-domain.com
   ```

4. Run the database initialization and the bot:
   ```bash
   python main.py
   ```

5. Run the local FastAPI redirect server (if testing locally on port 8000):
   ```bash
   uvicorn redirect_server:app --host 0.0.0.0 --port 8000 --reload
   ```

---

## License 📄
This project is open-source and licensed under the MIT License.
