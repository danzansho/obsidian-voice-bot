import aiosqlite

DB_PATH = "users.db"

# Initialize the database and create the users table if it doesn't exist
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                obsidian_path TEXT
            )
        """)
        await db.commit()

# Save or update the Obsidian path for a specific user
async def save_user_path(user_id: int, path: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO users (user_id, obsidian_path)
            VALUES (?, ?)
        """, (user_id, path))
        await db.commit()

# Retrieve the Obsidian path for a specific user
async def get_user_path(user_id: int) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT obsidian_path FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None