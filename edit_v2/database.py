import aiosqlite
import asyncio
import os

DB_PATH = "edit_v2.db"

class Database:

    def __init__(self):
        self.db_path = DB_PATH

    async def initialize(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                log_channel_id INTEGER,
                mod_role_id INTEGER,
                setup_completed INTEGER DEFAULT 0
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

            await db.execute("""
            CREATE TABLE IF NOT EXISTS logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                action TEXT,
                user_id INTEGER,
                moderator_id INTEGER,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """)

            await db.commit()

    async def execute(self, query: str, params: tuple = ()):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(query, params)
            await db.commit()

    async def fetchone(self, query: str, params: tuple = ()):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                return await cursor.fetchone()

    async def fetchall(self, query: str, params: tuple = ()):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                return await cursor.fetchall()
