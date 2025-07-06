import logging
import json
import re
import os
import config
import functools
import traceback
import asyncio
import hashlib
from collections import defaultdict
from logging.handlers import TimedRotatingFileHandler
from telethon import TelegramClient, events
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler(
    "bot.log", when="midnight", interval=1, backupCount=30, encoding='utf-8'
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

client = TelegramClient(config.session_name, config.api_id, config.api_hash)

message_buffer = defaultdict(list)
flush_tasks = {}
suppressed_keys = set()
BUFFER_TIME = 2.0
pending_reviews = {}

review_group_entity = None
target_channel_entity = None
admin_notify_entity = None
source_entities = []

def load_keywords(path: str) -> list[str]:
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        return []
    return data if isinstance(data, list) else data.get("keywords", [])

def safe_handler(func):
    @functools.wraps(func)
    async def wrapper(event, *args, **kwargs):
        try:
            await func(event, *args, **kwargs)
        except Exception as e:
            msg = getattr(event, "message", None)
            text = msg.message if msg and msg.message else "无消息文本"
            try:
                channel = await event.get_chat()
                channel_title = channel.title or "未知"
            except:
                channel_title = "未知"
            logging.error(
                f"❌ 异常 | 来源：{channel_title} | 内容：{text} | 错误：{e}\n{traceback.format_exc()}"
            )
    return wrapper

async def download_message_with_unique_name(message, base_dir='/tmp'):
    os.makedirs(base_dir, exist_ok=True)
    timestamp = message.date.strftime("%Y%m%d_%H%M%S_%f")
    sender_id = message.sender_id or "unknown"
    ext = ".bin"
    if message.document and message.document.mime_type:
        if "video" in message.document.mime_type:
            ext = ".mp4"
        elif "image" in message.document.mime_type:
            ext = ".jpg"
        elif "pdf" in message.document.mime_type:
            ext = ".pdf"
    elif message.photo:
        ext = ".jpg"
    elif message.video:
        ext = ".mp4"
    base_name = f"{timestamp}_{sender_id}"
    file_path = os.path.join(base_dir, base_name + ext)
    counter = 1
    while os.path.exists(file_path):
        file_path = os.path.join(base_dir, f"{base_name}_{counter}{ext}")
        counter += 1
    saved_path = await message.download_media(file=file_path)
    return saved_path

async def flush_buffer(key):
    await asyncio.sleep(BUFFER_TIME)
    if key in suppressed_keys:
        suppressed_keys.discard(key)
        flush_tasks.pop(key, None)
        message_buffer.pop(key, None)
        return

    msgs = message_buffer.pop(key, [])
    flush_tasks.pop(key, None)
    if not msgs:
        return

    texts = [m.message.strip() for m in msgs if m.message and m.message.strip()]
    combined_text = "\n".join(texts) if texts else ""
    files = []
    for m in msgs:
        if m.media:
            try:
                path = await download_message_with_unique_name(m)
                if path:
                    files.append(path)
            except Exception as e:
                logging.error(f"下载媒体失败: {e}")

    if config.channel_info.short_url and config.channel_info.short_url not in combined_text:
        combined_text += f"\n{config.channel_info.title}\n{config.channel_info.url}\n{config.channel_info.contact}"

    md5_hash = hashlib.md5(combined_text.encode('utf-8')).hexdigest()
    try:
        with open(config.md5_file, 'r', encoding='utf-8') as f:
            sent_hashes = f.read().splitlines()
    except FileNotFoundError:
        sent_hashes = []
    if md5_hash in sent_hashes:
        logging.info(f"⏭️ 已发送过内容({md5_hash})，跳过")
        return
    with open(config.md5_file, 'a', encoding='utf-8') as f:
        f.write(md5_hash + '\n')
    with open(config.md5_file, 'r+', encoding='utf-8') as f:
        lines = f.readlines()
        if len(lines) > 2000:
            f.seek(0)
            f.writelines(lines[-2000:])

    review_caption = f"{combined_text}\n\n✅ 发送 /publish 🚀 发布全部\n✅ 回复 /publish 📄 只发布此条。\n🚫 回复 /reject ❌ 拒绝此条。"
    try:
        review_msg = await client.send_file(review_group_entity, files, caption=review_caption) if files else \
                     await client.send_message(review_group_entity, review_caption)

        if isinstance(review_msg, list):
            review_msg = review_msg[0]
        logging.info(f"保存 pending_reviews id={review_msg.id}")

        pending_reviews[review_msg.id] = {
            "files": files,
            "text": combined_text,
            "md5": md5_hash,
            "created": datetime.now(),
            "review_group": review_group_entity
        }
        logging.info(f"🚀 已发送到审核群 message_id={review_msg.id}")
    except Exception as e:
        logging.error(f"发送审核消息失败: {e}")

async def publish_content(files, text):
    try:
        if files:
            await client.send_file(target_channel_entity, files, caption=text)
        else:
            await client.send_message(target_channel_entity, text)
        await client.send_message(admin_notify_entity, f"✅ 已发布内容")
    except Exception as e:
        logging.error(f"发布内容失败: {e}")

async def auto_publish_pending_reviews():
    while True:
        now = datetime.now()
        expired = []
        for rid, item in list(pending_reviews.items()):
            if (now - item["created"]).total_seconds() > 1800:
                try:
                    await publish_content(item["files"], item["text"])
                    await client.send_message(
                        admin_notify_entity,
                        f"⏳ 超过30分钟未审核，已自动发布 message_id={rid}"
                    )
                    await client.delete_messages(item["review_group"], rid)
                except Exception as e:
                    logging.error(f"自动发布失败: {e}")
                expired.append(rid)
        for rid in expired:
            pending_reviews.pop(rid, None)
        await asyncio.sleep(300)

@client.on(events.NewMessage)
@safe_handler
async def review_commands(event):
    try:
        chat = await event.get_chat()
    except Exception as e:
        logging.warning(f"检测 chat_id 失败: {e}")

    text = event.raw_text.strip().lower()
    reply = await event.get_reply_message()

    if text == "/publish":
        if reply and reply.id in pending_reviews:
            item = pending_reviews.pop(reply.id)
            await publish_content(item["files"], item["text"])
            await client.delete_messages(event.chat_id, reply.id)
            logging.info(f"✅ 已单条发布 message_id={reply.id}")
        else:
            for rid, item in list(pending_reviews.items()):
                await publish_content(item["files"], item["text"])
                await client.delete_messages(item["review_group"], rid)
                pending_reviews.pop(rid, None)
                logging.info(f"✅ 已批量发布 message_id={rid}")
    elif text == "/reject":
        if reply and reply.id in pending_reviews:
            await client.send_message(admin_notify_entity, f"🚫 有内容被拒绝")
            await client.delete_messages(event.chat_id, reply.id)
            pending_reviews.pop(reply.id, None)
            logging.info(f"❌ 已拒绝 message_id={reply.id}")

async def main():
    global review_group_entity, target_channel_entity, admin_notify_entity, source_entities
    await client.start()
    logging.info("✅ Bot 已启动")

    review_group_entity = await client.get_entity(config.review_groups[0])
    target_channel_entity = await client.get_entity(config.target_channel)
    admin_notify_entity = await client.get_entity(config.admin_notify_group)
    source_entities = []
    for ch in config.source_channels:
        try:
            ent = await client.get_entity(ch)
            source_entities.append(ent)
            logging.info(f"✅ 已解析 source_channel: {ch} -> {ent.id}")
        except Exception as e:
            logging.error(f"⚠️ 无法获取频道 {ch}: {e}")

    logging.info(f"✅ 已解析所有频道群")
    asyncio.create_task(auto_publish_pending_reviews())

    @client.on(events.NewMessage(chats=source_entities))
    @safe_handler
    async def handler(event):
        m = event.message
        if not (m.message or m.media):
            return
        chat = await event.get_chat()
        sender = await event.get_sender()
        key = (chat.id, sender.id)
        text = m.message or ""
        if text.strip():
            ad_keywords = load_keywords("ad_keywords.json")
            for k in ad_keywords:
                if k in text:
                    task = flush_tasks.pop(key, None)
                    if task:
                        task.cancel()
                    message_buffer.pop(key, None)
                    suppressed_keys.add(key)
                    return
            text = re.sub(r'^(?=.*https?://)(?!.*t\.me).*$', '', text, flags=re.MULTILINE)
            del_keywords = load_keywords("keywords.json")
            pattern = re.compile(rf'^(?=.*(?:{"|".join(del_keywords)})).*$', re.MULTILINE)
            text, cnt = pattern.subn('', text)
            if cnt >= 7:
                return
            text = re.sub(r'\n+', '\n', text).strip()
            for old, new in config.replacements.items():
                text = text.replace(old, new)
            for pat, rep in config.ad_replacements.items():
                text = re.sub(pat, rep, text, flags=re.MULTILINE)
            if config.channel_info.short_url and config.channel_info.short_url not in text:
                text += f"\n{config.channel_info.title}\n{config.channel_info.url}\n{config.channel_info.contact}"
            m.message = text
        message_buffer[key].append(m)
        if key not in flush_tasks:
            flush_tasks[key] = asyncio.create_task(flush_buffer(key))

    logging.info("📡 正在监听...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
