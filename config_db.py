import sqlite3
import json
from types import SimpleNamespace

DB_PATH = "config.db"

def init_config_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 全局配置
    c.execute("""
    CREATE TABLE IF NOT EXISTS global_config (
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    # 频道
    c.execute("""
    CREATE TABLE IF NOT EXISTS channels (
        type TEXT,   -- target/review/admin/source
        value TEXT
    )""")
    # 替换规则
    c.execute("""
    CREATE TABLE IF NOT EXISTS replacements (
        src TEXT PRIMARY KEY,
        dst TEXT
    )""")
    # 广告过滤规则
    c.execute("""
    CREATE TABLE IF NOT EXISTS ad_replacements (
        pattern TEXT PRIMARY KEY,
        dst TEXT
    )""")
    conn.commit()
    conn.close()

def set_global_config(key, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO global_config (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_global_config(key, default=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM global_config WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else default

def get_channels(type_):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT value FROM channels WHERE type=?", (type_,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_replacements():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT src, dst FROM replacements")
    rows = c.fetchall()
    conn.close()
    return dict(rows)

def get_ad_replacements():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT pattern, dst FROM ad_replacements")
    rows = c.fetchall()
    conn.close()
    return dict(rows)

def set_replacements(replace_dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for src, dst in replace_dict.items():
        c.execute("INSERT OR REPLACE INTO replacements (src, dst) VALUES (?, ?)", (src, dst))
    conn.commit()
    conn.close()

def set_ad_replacements(ad_dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    for pattern, dst in ad_dict.items():
        c.execute("INSERT OR REPLACE INTO ad_replacements (pattern, dst) VALUES (?, ?)", (pattern, dst))
    conn.commit()
    conn.close()