import asyncio
import yaml
import sqlite3
import random
import datetime
import argparse
import logging
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

# Logging configuration: write to file and console
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.INFO,
    format=log_format,
    handlers=[
        logging.FileHandler('sender.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

send_switch = False  # 控制是否发送消息

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
            sent_flag INTEGER DEFAULT 0,
            username TEXT,
            phone TEXT,
            first_name TEXT,
            last_name TEXT
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
    conn.commit()
    conn.close()
    logger.info("数据库初始化完成: %s", DB_FILE)

def read_config():
    with open(CONFIG_FILE, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    logger.info("配置加载完成: %s", CONFIG_FILE)
    return cfg

def get_today():
    return datetime.date.today().isoformat()

async def get_all_discussion_groups(client, channel_links):
    groups = []
    for link in channel_links:
        try:
            channel_username = link.rstrip("/").split("/")[-1]
            channel_entity = await client.get_entity(channel_username)
            full = await client(GetFullChannelRequest(channel_entity))
            linked_chat_id = full.full_chat.linked_chat_id
            if not linked_chat_id:
                logger.warning("频道 %s 没有关联讨论群，跳过", link)
                continue
            group_id = -int(f"100{linked_chat_id}")
            input_entity = await client.get_input_entity(group_id)
            groups.append(input_entity)
            logger.info("关联讨论群: 频道 %s -> 群 %s", channel_entity.id, group_id)
        except Exception as e:
            logger.error("获取频道 %s 的讨论群失败: %s", link, e)
    return groups

async def process_users_from_db(client, session_name, max_per_day, min_delay, max_delay, message_text):
    conn = sqlite3.connect(DB_FILE, timeout=30)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()
    today = get_today()

    async with DB_LOCK:
        cur.execute("SELECT count FROM daily_counts WHERE session=? AND date=?", (session_name, today))
        row = cur.fetchone()
        sent_today = row[0] if row else 0

    async with DB_LOCK:
        cur.execute("SELECT user_id FROM sent_users WHERE sent_flag=0")
        users = cur.fetchall()

    random.shuffle(users)

    for (uid_str,) in users:
        if sent_today >= max_per_day:
            logger.info("[%s] 达到每日上限 %d", session_name, max_per_day)
            break

        try:
            if send_switch:
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

                logger.info("[%s] 已发 %d/%d 给 %s", session_name, sent_today, max_per_day, uid_str)
                await asyncio.sleep(random.uniform(min_delay, max_delay))
            else:
                # logger.info("[%s] 发送功能已关闭，跳过用户 %s", session_name, uid_str)

        except FloodWaitError as e:
            logger.warning("[%s] FloodWait 等待 %ds", session_name, e.seconds)
            await asyncio.sleep(e.seconds + 5)

        except (UserPrivacyRestrictedError, ChatWriteForbiddenError, PeerIdInvalidError) as e:
            logger.warning("[%s] 用户 %s 因隐私/禁止发信，标记为-1", session_name, uid_str)
            async with DB_LOCK:
                cur.execute(
                    "UPDATE sent_users SET sent_flag=-1, last_sent_date=? WHERE user_id=?",
                    (today, uid_str)
                )
                conn.commit()

        except RPCError as e:
            logger.error("[%s] RPCError: %s", session_name, e)

        except Exception as ex:
            logger.error("[%s] 发信给 %s 失败: %s", session_name, uid_str, ex)

    conn.close()

async def run_account(account, channel_links, max_per_day, min_delay, max_delay, message_text):
    client = TelegramClient(account["session"], account["api_id"], account["api_hash"])
    await client.start()

    groups = await get_all_discussion_groups(client, channel_links)
    if not groups:
        logger.warning("[%s] 没有可用讨论群，退出监听", account["session"])
        return
    logger.info("[%s] 已开始监听 %d 个讨论群...", account["session"], len(groups))

    @client.on(events.NewMessage(chats=groups))
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
            cur.execute(
                """
                INSERT OR IGNORE INTO sent_users 
                (user_id, last_sent_date, sent_flag, username, phone, first_name, last_name)
                VALUES (?, ?, 0, ?, ?, ?, ?)
                """, (uid_str, today, username, phone, first_name, last_name)
            )
            conn.commit()
        conn.close()
        logger.info("[%s] [监听] 记录用户 %s (@%s)", account["session"], uid_str, username)

    asyncio.create_task(cycle_send(client, account["session"], max_per_day, min_delay, max_delay, message_text))
    await client.run_until_disconnected()

async def cycle_send(client, session_name, max_per_day, min_delay, max_delay, message_text):
    while True:
        await process_users_from_db(client, session_name, max_per_day, min_delay, max_delay, message_text)
        await asyncio.sleep(random.uniform(10, 20))

async def reset_counts():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cur = conn.cursor()
    today = get_today()
    cur.execute("DELETE FROM daily_counts WHERE date!=?", (today,))
    conn.commit()
    conn.close()
    logger.info("重置每日计数完成")

async def show_stats():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cur = conn.cursor()
    today = get_today()
    logger.info("=== 今日发送统计 ===")
    for session, date, count in cur.execute(
        "SELECT session,date,count FROM daily_counts WHERE date=?", (today,)
    ):
        logger.info("%s: %s", session, count)
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
            run_account(acc, channel_links, max_per_day, min_delay, max_delay, msg)
            for acc in cfg.get("accounts", [])
        ])
    else:
        p.print_help()

if __name__ == "__main__":
    asyncio.run(main())
