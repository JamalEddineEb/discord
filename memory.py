import aiosqlite
import json

DB_FILE = "server_memory.db"

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        print("init db")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                personality TEXT DEFAULT 'friendly',
                messages TEXT DEFAULT '[]'
            )
        """)
        await db.commit()


async def update_user_memory(user_id, username, message):
    async with aiosqlite.connect(DB_FILE) as db:
        # Check if user exists
        cursor = await db.execute("SELECT messages FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()

        if row:
            messages = json.loads(row[0])
        else:
            messages = []

        message = f'{username} : {message}'

        # Add the new message (limit history to avoid bloat)
        messages.append(message)

        if row:
            await db.execute("UPDATE users SET messages = ? WHERE user_id = ?", (json.dumps(messages), user_id))
        else:
            await db.execute("INSERT INTO users (user_id, username, messages) VALUES (?, ?, ?)", 
                             (user_id, username, json.dumps(messages)))

        await db.commit()


async def get_conversation_memory():
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT personality, messages FROM users")
        row = await cursor.fetchone()

        if row:
            personality = row[0]
            messages = json.loads(row[1])
        else:
            personality = "friendly"
            messages = []
            print(messages)

    return personality, messages
