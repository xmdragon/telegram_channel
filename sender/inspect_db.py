#!/usr/bin/env python3
import sqlite3

DB_FILE = "database.db"

def show_users_by_flag(flag):
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cur = conn.cursor()
    cur.execute("""
        SELECT user_id, username, phone, first_name, last_name, last_sent_date 
        FROM sent_users
        WHERE sent_flag=?
    """, (flag,))
    rows = cur.fetchall()
    print(f"\n=== sent_flag={flag} 共 {len(rows)} 用户 ===")
    for row in rows:
        uid, username, phone, fname, lname, last_date = row
        print(f"ID:{uid}  @{username}  {fname} {lname} 📞{phone}  最后: {last_date}")
    conn.close()

def show_summary():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cur = conn.cursor()
    for flag in [0,1,-1]:
        cur.execute("SELECT count(*) FROM sent_users WHERE sent_flag=?", (flag,))
        count = cur.fetchone()[0]
        print(f"sent_flag={flag}: {count} 用户")
    conn.close()

if __name__ == "__main__":
    print("=== sent_users 总览 ===")
    show_summary()
    show_users_by_flag(0)
    show_users_by_flag(1)
    show_users_by_flag(-1)
