import logging
import json
import re
import config
import traceback
import asyncio
import os
import glob
import sqlite3
import random
from logging.handlers import TimedRotatingFileHandler
from telethon import TelegramClient, events
from telethon.errors import ChannelPrivateError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

# 清理残留锁文件
for file in glob.glob("*.session-journal"):
    os.remove(file)

client = TelegramClient(config.session_name, config.api_id, config.api_hash)

# 日志配置
def setup_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = TimedRotatingFileHandler(
        "get_history.log", when="midnight", interval=1, backupCount=30, encoding='utf-8'
    )
    handler.suffix = "%Y-%m-%d"
    class JsonFormatter(logging.Formatter):
        def format(self, record):
            return json.dumps({
                "time": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
                "level": record.levelname,
                "message": record.getMessage()
            }, ensure_ascii=False)
    json_formatter = JsonFormatter()
    handler.setFormatter(json_formatter)
    logger.addHandler(handler)
    console = logging.StreamHandler()
    console.setFormatter(json_formatter)
    logger.addHandler(console)

setup_logger()

# 加载关键词
def load_keywords(path: str) -> list[str]:
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    return data if isinstance(data, list) else data.get("keywords", [])

DB_FILE = "reviews.db"
# 初始化数据库
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS pending_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_channel TEXT,
            source_message_id INTEGER,
            review_message_id INTEGER,
            group_id INTEGER,
            text TEXT,
            file_id TEXT,
            published INTEGER DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()
init_db()

# 文本过滤
def process_text(msg):
    text = msg.message or ''
    ad_keywords = load_keywords("ad_keywords.json")
    if any(k in text for k in ad_keywords):
        return None
    text = re.sub(r'^(?=.*https?://)(?!.*t\.me).*$', '', text, flags=re.MULTILINE)
    keywords = load_keywords("keywords.json")
    pattern_str = '|'.join(keywords)
    pattern = re.compile(rf'^(?=.*(?:{pattern_str})).*$', re.MULTILINE)
    text, count = pattern.subn('', text)
    if count >= 7:
        return None
    text = re.sub(r'\n+', '\n', text).strip()
    for old, new in config.replacements.items():
        text = text.replace(old, new)
    for p, r in config.ad_replacements.items():
        text = re.sub(p, r, text, flags=re.MULTILINE)
    if getattr(config, 'channel_info', None) and config.channel_info.short_url:
        if config.channel_info.short_url not in text:
            text += f"\n{config.channel_info.title}\n{config.channel_info.url}\n{config.channel_info.contact}"
    return text

async def main():
    await client.start()
    logging.info("🚀 TelegramClient 已启动")

    # 获取实体
    review_groups = config.review_groups  # list of chat ID or username
    admin_notify = getattr(config, 'admin_notify_group', None)

    # 预拉取 source channels
    for ch in config.source_channels:
        try:
            await client.get_entity(ch)
            logging.info(f"✅ 已解析 source_channel: {ch}")
        except Exception as e:
            logging.error(f"⚠️ 无法解析 source_channel {ch}: {e}")

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # 采集历史消息
    # 采集历史消息（跨频道按时间排序）
    new_msgs = []
    # 1. 把每个频道的未处理消息都拉出来
    for ch in config.source_channels:
        # 找到上次处理到的 message_id
        cur.execute(
            "SELECT MAX(source_message_id) FROM pending_reviews WHERE source_channel=?",
            (ch)
        )
        last_id = cur.fetchone()[0] or 0
        logging.info(f"📌 从 {ch} 的 {last_id} 开始继续采集")
        try:
            channel = await client.get_entity(ch)
            async for msg in client.iter_messages(channel, offset_id=last_id, reverse=True):
                # 收集到列表，后面统一排序
                new_msgs.append((msg.date, ch, msg))
                # 先把消息文本取出来，None 时变成空串，再截取前 30 个字符
                text_preview = (msg.message or "视频或图片")[:30]
                logging.info(f"📥 采集到 {ch} 的消息 {msg.id} {text_preview}...")
        except ChannelPrivateError:
            try:
                await client(JoinChannelRequest(ch))
                logging.info(f"✅ 已加入 {ch}，继续采集")
            except Exception as e:
                logging.error(f"🚨 加入 {ch} 失败: {e}")
        except Exception:
            logging.error(f"🚨 采集 {ch} 出错: {traceback.format_exc()}")

    # 2. 按时间排序（从最旧到最新）
    new_msgs.sort(key=lambda x: x[0])

    # 3. 按顺序发布到审核群
    for _, ch, msg in new_msgs:
        text = process_text(msg)
        if not text:
            continue
        logging.info(f"📄 采集 {ch}:{msg.id} {text[:30]}...")
        file_arg = msg.media if isinstance(msg.media, (MessageMediaPhoto, MessageMediaDocument)) else None
        preview = (
            f"{text}\n\n"
            "✅ /publish 发布全部\n"
            "✅ 回复 /publish 发布此条\n"
            "🚫 回复 /reject 拒绝此条"
        )
        for group in review_groups:
            sent = await client.send_message(group, preview, file=file_arg)
            cur.execute(
                "INSERT INTO pending_reviews "
                "(source_channel, source_message_id, review_message_id, group_id, text, file_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (ch, msg.id, sent.id, group, text, str(file_arg))
            )
            logging.info(f"🔔 消息已发至群 {group} 作为 id={sent.id}")
        # 为了避免触发限流，稍作休眠
        await asyncio.sleep(random.randint(5, 10))

    conn.commit()
    await client.run_until_disconnected()

# 命令处理——仅在审核群监听
@client.on(events.NewMessage)
async def commands(event):
    try:
        text = event.raw_text.strip().lower()
        reply_id = event.message.reply_to_msg_id
        logging.info(f"🔍 收到命令 '{text}' 来自 {event.chat_id} 回复ID={reply_id}")

        conn = sqlite3.connect(DB_FILE)
        cur = conn.cursor()

        target_channel = config.target_channel

        if text == "/publish":
            if reply_id:
                # 单条发布
                cur.execute(
                    "SELECT id, text, file_id FROM pending_reviews WHERE review_message_id=? AND group_id=? AND published=0",
                    (reply_id, event.chat_id)
                )
                row = cur.fetchone()
                if row:
                    await client.send_message(target_channel, row[1], file=eval(row[2]))
                    cur.execute("UPDATE pending_reviews SET published=1 WHERE id=?", (row[0],))
                    await client.delete_messages(event.chat_id, reply_id)
                    await event.reply("✅ 单条已发布并删除")
                    #logging.info(f"✅ 单条发布 id={reply_id}")
                else:
                    await event.reply("⚠️ 此消息已处理或未找到")
            else:
                # 批量发布
                cur.execute("SELECT id, text, file_id, review_message_id, group_id FROM pending_reviews WHERE published=0")
                rows = cur.fetchall()
                for r in rows:
                    media = None
                    try:
                        media = eval(r[2])
                    except Exception:
                        media = None
                    await client.send_message(target_channel, r[1], file=media)
                    cur.execute("UPDATE pending_reviews SET published=1 WHERE id=?", (r[0],))
                    await client.delete_messages(r[4], r[3])
                    #logging.info(f"✅ 批量发布 id={r[3]}")
                if rows:
                    await event.reply(f"✅ 已发布全部({len(rows)} 条)")
                else:
                    await event.reply("⚠️ 无待发布消息")

        elif text == "/reject" and reply_id:
            # 单条拒绝
            cur.execute(
                "UPDATE pending_reviews SET published=1 WHERE review_message_id=? AND group_id=?",
                (reply_id, event.chat_id)
            )
            conn.commit()
            await client.delete_messages(event.chat_id, reply_id)
            await event.reply("🚫 单条已拒绝并删除")
            #logging.info(f"❌ 单条拒绝 id={reply_id}")

        conn.commit()
        conn.close()
    except Exception:
        logging.error(f"🚨 命令处理异常:{traceback.format_exc()}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 中断退出")
    except Exception:
        logging.error(f"🚨 主异常: {traceback.format_exc()}")
