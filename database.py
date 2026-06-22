import aiosqlite

DB_PATH = "users.db"

# Initialize database with notes counter (limit: 0 by default)
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                obsidian_path TEXT,
                notes_created INTEGER DEFAULT 0
            )
        """)
        await db.commit()

# Save or update path
async def save_user_path(user_id: int, path: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, obsidian_path)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET obsidian_path = excluded.obsidian_path
        """, (user_id, path))
        await db.commit()

# Increment notes counter for a specific user
async def increment_notes_counter(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users
            SET notes_created = notes_created + 1
            WHERE user_id = ?
        """, (user_id,))
        await db.commit()

# Get user data (path and total notes count)
async def get_user_data(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT obsidian_path, notes_created FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"path": row[0], "notes_created": row[1]}
            return None