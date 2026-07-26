import aiosqlite
import json

DB_FILE = "bot_data.db"

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        # Create users table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        # Create signals table
        await db.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                type TEXT,
                entry REAL,
                tp REAL,
                tp2 REAL,
                sl REAL,
                status TEXT,
                timestamp TEXT,
                message_ids TEXT,
                stars INTEGER DEFAULT 5
            )
        ''')
        
        # Migratsiya: eski jadvallarga 'stars' va 'tp2' ustunini qo'shish
        try:
            await db.execute("ALTER TABLE signals ADD COLUMN stars INTEGER DEFAULT 5")
        except Exception:
            pass # Ustun allaqachon bo'lishi mumkin
            
        try:
            await db.execute("ALTER TABLE signals ADD COLUMN tp2 REAL")
        except Exception:
            pass
            
        await db.commit()

async def add_user(user_id: int):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
        await db.commit()

async def get_all_users() -> list:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def add_signal(symbol, sig_type, entry, tp, tp2, sl, status, timestamp, message_ids, stars=5):
    async with aiosqlite.connect(DB_FILE) as db:
        msg_json = json.dumps(message_ids)
        await db.execute('''
            INSERT INTO signals (symbol, type, entry, tp, tp2, sl, status, timestamp, message_ids, stars)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, sig_type, entry, tp, tp2, sl, status, timestamp, msg_json, stars))
        await db.commit()

async def get_pending_signals() -> list:
    async with aiosqlite.connect(DB_FILE) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM signals WHERE status IN ('PENDING', 'TP1_HIT')") as cursor:
            return await cursor.fetchall()

async def update_signal_status(signal_id, status):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('UPDATE signals SET status = ? WHERE id = ?', (status, signal_id))
        await db.commit()

async def update_signal_sl(signal_id, sl):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('UPDATE signals SET sl = ? WHERE id = ?', (sl, signal_id))
        await db.commit()

async def get_weekly_signals_stats(start_time_iso: str):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('''
            SELECT stars, status, COUNT(*) as count 
            FROM signals 
            WHERE timestamp > ? AND status IN ('WIN', 'LOSS', 'BREAK_EVEN')
            GROUP BY stars, status
        ''', (start_time_iso,)) as cursor:
            return await cursor.fetchall()

async def get_daily_coin_stats(start_time_iso: str):
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('''
            SELECT stars, symbol, status, COUNT(*) as count 
            FROM signals 
            WHERE timestamp > ? AND status IN ('WIN', 'LOSS', 'BREAK_EVEN')
            GROUP BY stars, symbol, status
        ''', (start_time_iso,)) as cursor:
            return await cursor.fetchall()

# Yangiliklar xotirasi (oxirgi yangilik sarlavhasi)
async def get_last_news_link() -> str:
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value TEXT)''')
        async with db.execute("SELECT value FROM kv_store WHERE key='last_news'") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else ""

async def save_last_news_link(link: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS kv_store (key TEXT PRIMARY KEY, value TEXT)''')
        await db.execute("INSERT OR REPLACE INTO kv_store (key, value) VALUES ('last_news', ?)", (link,))
        await db.commit()
