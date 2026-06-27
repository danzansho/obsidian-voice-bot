import aiosqlite

DB_PATH = "users.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                notes_created INTEGER DEFAULT 0,
                vault_name TEXT
            )
        """)
        # Schema migration: Add vault_name column if it does not exist
        try:
            await db.execute("ALTER TABLE users ADD COLUMN vault_name TEXT")
        except aiosqlite.OperationalError:
            pass  # Column already exists
        await db.commit()

async def register_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users (user_id)
            VALUES (?)
        """, (user_id,))
        await db.commit()

async def set_user_vault(user_id: int, vault_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users SET vault_name = ? WHERE user_id = ?
        """, (vault_name, user_id))
        await db.commit()

async def try_increment_notes_counter(user_id: int, limit: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            UPDATE users
            SET notes_created = notes_created + 1
            WHERE user_id = ? AND notes_created < ?
        """, (user_id, limit))
        await db.commit()
        return cursor.rowcount > 0

async def decrement_notes_counter(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE users
            SET notes_created = notes_created - 1
            WHERE user_id = ? AND notes_created > 0
        """, (user_id,))
        await db.commit()

async def get_user_data(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT notes_created, vault_name FROM users WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {"notes_created": row[0], "vault_name": row[1]}
            return None