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