import aiosqlite
import asyncio

DB_NAME = "edit_v2.db"

class Database:
    def __init__(self):
        self.db = None

    async def connect(self):
        self.db = await aiosqlite.connect(DB_NAME)
        await self.setup_tables()

    async def setup_tables(self):
        await self.db.executescript("""
        CREATE TABLE IF NOT EXISTS guild_config (
            guild_id INTEGER PRIMARY KEY,
            log_channel INTEGER,
            greet_channel INTEGER,
            leave_channel INTEGER
        );

        CREATE TABLE IF NOT EXISTS warns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            moderator_id INTEGER,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            action TEXT,
            moderator_id INTEGER,
            reason TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """)
        await self.db.commit()

    async def execute(self, query, *args):
        await self.db.execute(query, args)
        await self.db.commit()

    async def fetch(self, query, *args):
        cursor = await self.db.execute(query, args)
        return await cursor.fetchall()

    async def fetchone(self, query, *args):
        cursor = await self.db.execute(query, args)
        return await cursor.fetchone()
