import sqlite3

def get_db_connection():
    conn = sqlite3.connect('telegram.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            channel_id INTEGER,
            text TEXT,
            date TEXT,
            edited INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()
