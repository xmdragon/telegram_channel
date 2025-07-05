import asyncio
import yaml
import sqlite3
import random
import datetime
import argparse
from sqlite3 import OperationalError
from telethon import TelegramClient, events
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.errors import (
    RPCError,
    UserPrivacyRestrictedError,
    PeerIdInvalidError,
    FloodWaitError,
    ChatWriteForbiddenError
)

DB_FILE = "database.db"
CONFIG_FILE = "config.yaml"
DB_LOCK = asyncio.Lock()


def init_db():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sent_users (
            user_id TEXT PRIMARY KEY,
            last_sent_date TEXT,
            sent_flag INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_counts (
            session TEXT,
            date TEXT,
            count INTEGER,
            PRIMARY KEY (session, date)
        )
    """)
    # 自动添加新字段
    try: cur.execute("ALTER TABLE sent_users ADD COLUMN username TEXT")
    except sqlite3.OperationalError: pass
    try: cur.execute("ALTER TABLE sent_users ADD COLUMN phone TEXT")
    except sqlite3.OperationalError: pass
    try: cur.execute("ALTER TABLE sent_users ADD COLUMN first_name TEXT")
    except sqlite3.OperationalError: pass
    try: cur.execute("ALTER TABLE sent_users ADD COLUMN last_name TEXT")
    except sqlite3.OperationalError: pass

    conn.commit()
    conn.close()


def read_config():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_today():
    return datetime.date.today().isoformat()


async def get_discussion_group_entity(client, channel_link):
    channel_username = channel_link.rstrip("/").split("/")[-1]
    channel_entity = await client.get_entity(channel_username)
    full = await client(GetFullChannelRequest(channel_entity))
    linked_chat_id = full.full_chat.linked_chat_id
    if not linked_chat_id:
        raise ValueError(f"{channel_link} 没有关联讨论群")
    group_id = -int(f"100{linked_chat_id}")
    input_entity = await client.get_input_entity(group_id)
    info = input_entity.to_dict()
    if 'channel_id' not in info:
        raise ValueError(f"{channel_link} 关联群非 megagroup，跳过")
    print(f"[+] 频道 {channel_entity.id} 关联到讨论群 {group_id}")
    return channel_entity.id, input_entity


async def process_group(client, session_name, group_entity):
    today = get_today()
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    async for user in client.iter_participants(group_entity):
        uid_str = str(user.id)
        username = user.username or ""
        phone = user.phone or ""
        first_name = user.first_name or ""
        last_name = user.last_name or ""

        async with DB_LOCK:
            cur.execute("""
                INSERT OR IGNORE INTO sent_users 
                (user_id, last_sent_date, sent_flag, username, phone, first_name, last_name)
                VALUES (?, ?, 0, ?, ?, ?, ?)
            """, (uid_str, today, username, phone, first_name, last_name))
            conn.commit()
        print(f"[{session_name}] 已记录用户 {uid_str} (@{username})")

    conn.close()


async def process_users_from_db(client, session_name, max_per_day, min_delay, max_delay, message_text):
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()
    today = get_today()

    async with DB_LOCK:
        cur.execute(
            "SELECT count FROM daily_counts WHERE session=? AND date=?",
            (session_name, today)
        )
        row = cur.fetchone()
        sent_today = row[0] if row else 0

    async with DB_LOCK:
        cur.execute("SELECT user_id FROM sent_users WHERE sent_flag=0")
        users = cur.fetchall()

    random.shuffle(users)

    for (uid_str,) in users:
        if sent_today >= max_per_day:
            print(f"[{session_name}] 达到每日上限 {max_per_day}")
            break

        try:
            await client.send_message(int(uid_str), message_text)
            sent_today += 1

            async with DB_LOCK:
                cur.execute(
                    "UPDATE sent_users SET sent_flag=1, last_sent_date=? WHERE user_id=?",
                    (today, uid_str)
                )
                cur.execute(
                    "INSERT OR REPLACE INTO daily_counts(session, date, count) VALUES(?,?,?)",
                    (session_name, today, sent_today)
                )
                conn.commit()

            print(f"[{session_name}] 已发 {sent_today}/{max_per_day} 给 {uid_str}")
            await asyncio.sleep(random.uniform(min_delay, max_delay))

        except FloodWaitError as e:
            print(f"[{session_name}] FloodWait 等待 {e.seconds}s")
            await asyncio.sleep(e.seconds + 5)

        except (UserPrivacyRestrictedError, ChatWriteForbiddenError, PeerIdInvalidError) as e:
            print(f"[{session_name}] 用户 {uid_str} 因隐私/禁止发信，标记为-1")
            async with DB_LOCK:
                cur.execute(
                    "UPDATE sent_users SET sent_flag=-1, last_sent_date=? WHERE user_id=?",
                    (today, uid_str)
                )
                conn.commit()

        except RPCError as e:
            if "PRIVACY" in str(e).upper() or "PREMIUM_REQUIRED" in str(e).upper():
                print(f"[{session_name}] 用户 {uid_str} PRIVACY 错误，标记为-1")
                async with DB_LOCK:
                    cur.execute(
                        "UPDATE sent_users SET sent_flag=-1, last_sent_date=? WHERE user_id=?",
                        (today, uid_str)
                    )
                    conn.commit()
            else:
                print(f"[{session_name}] 其它 RPCError 跳过: {e}")

        except Exception as ex:
            print(f"[{session_name}] 发信给 {uid_str} 失败: {ex}")

    conn.close()


async def run_account(account, channel_links, max_per_day, min_delay, max_delay, message_text, is_listener=False):
    client = TelegramClient(account["session"], account["api_id"], account["api_hash"])
    await client.start()

    if is_listener:
        mappings = []
        for link in channel_links:
            try:
                channel_id, grp_ent = await get_discussion_group_entity(client, link)
                mappings.append((channel_id, grp_ent))
            except Exception as e:
                print(f"[{account['session']}] 跳过 {link}: {e}")
        if not mappings:
            print(f"[{account['session']}] 没有可用的讨论群，退出")
            return

        handlers_chats = [grp for _, grp in mappings]
        ids = [grp.channel_id for _, grp in mappings]
        print(f"[{account['session']}] 监听群 channel_ids：{ids}")

        for _, grp_ent in mappings:
            print(f"[{account['session']}] 历史遍历群 channel_id={grp_ent.channel_id}")
            await process_group(client, account["session"], grp_ent)

        @client.on(events.NewMessage(chats=handlers_chats))
        async def handler(event):
            uid = event.sender_id
            if uid is None or (isinstance(uid, int) and str(uid).startswith("-100")):
                return

            user = await event.get_sender()
            username = user.username or ""
            phone = user.phone or ""
            first_name = user.first_name or ""
            last_name = user.last_name or ""

            uid_str = str(uid)
            today = get_today()
            conn = sqlite3.connect(DB_FILE, timeout=30)
            conn.execute("PRAGMA journal_mode=WAL")
            cur = conn.cursor()
            async with DB_LOCK:
                cur.execute("""
                    INSERT OR IGNORE INTO sent_users 
                    (user_id, last_sent_date, sent_flag, username, phone, first_name, last_name)
                    VALUES (?, ?, 0, ?, ?, ?, ?)
                """, (uid_str, today, username, phone, first_name, last_name))
                conn.commit()
            conn.close()
            print(f"[{account['session']}] [监听] 记录用户 {uid_str} (@{username})")

        print(f"[{account['session']}] 开始实时监听")
        await client.run_until_disconnected()
    else:
        print(f"[{account['session']}] 只从数据库轮询用户发送私信")
        while True:
            await process_users_from_db(client, session_name=account["session"], max_per_day=max_per_day, min_delay=min_delay, max_delay=max_delay, message_text=message_text)
            await asyncio.sleep(random.uniform(10, 20))


async def reset_counts():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cur = conn.cursor()
    today = get_today()
    cur.execute("DELETE FROM daily_counts WHERE date!=?", (today,))
    conn.commit()
    conn.close()
    print("重置每日计数完成")


async def show_stats():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cur = conn.cursor()
    today = get_today()
    print("=== 今日发送统计 ===")
    for session, date, count in cur.execute(
        "SELECT session,date,count FROM daily_counts WHERE date=?", (today,)
    ):
        print(f"{session}: {count}")
    conn.close()


async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", action="store_true")
    p.add_argument("--stats", action="store_true")
    p.add_argument("--reset", action="store_true")
    args = p.parse_args()

    init_db()
    cfg = read_config()
    channel_links = [c["link"] for c in cfg.get("channels", [])]
    default_msg = "你好，欢迎订阅东南亚大事件「曝光」，链接: https://t.me/bigeventsinsea 😊"
    msg = cfg.get("message_text", default_msg)
    max_per_day = cfg.get("max_messages_per_day", 100)
    min_delay = cfg.get("min_delay", 5)
    max_delay = cfg.get("max_delay", 10)

    if args.reset:
        await reset_counts()
    elif args.stats:
        await show_stats()
    elif args.run:
        await asyncio.gather(*[
            run_account(acc, channel_links, max_per_day, min_delay, max_delay, msg, is_listener=(idx==0))
            for idx, acc in enumerate(cfg.get("accounts", []))
        ])
    else:
        p.print_help()


if __name__ == "__main__":
    asyncio.run(main())
