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


def load_keywords(path: str) -> list[str]:
    """读取关键词，支持两种 JSON 格式：列表或 {"keywords": [...]}"""
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        # logging.warning(f"⚠️ 关键词文件未找到：{path}")
        return []
    # 这里把 data 放进 f-string，以避免类型不匹配
    # logging.info(f"⚠️ 文件 {path} 内容: {data!r}")
    if isinstance(data, list):
        return data
    return data.get("keywords", [])


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
                channel_username = channel.username or "未知"
            except:
                channel_title = channel_username = "未知"
            logging.error(
                f"❌ 异常 | 来源：{channel_title} [{channel_username}] | "
                f"内容：{text} | 错误：{e}\n{traceback.format_exc()}"
            )
    return wrapper

# ─── JSON 日志配置 ─────────────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler(
    "bot.log", when="midnight", interval=1, backupCount=30, encoding='utf-8'
)
handler.suffix = "%Y-%m-%d"
class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "time": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "message": record.getMessage()
        }
        return json.dumps(log_record, ensure_ascii=False)
json_formatter = JsonFormatter()
handler.setFormatter(json_formatter)
logger.addHandler(handler)
console = logging.StreamHandler()
console.setFormatter(json_formatter)
logger.addHandler(console)
# ─────────────────────────────────────────────────────────────────────────────

client = TelegramClient(config.session_name, config.api_id, config.api_hash)

# ─── 合并发送缓冲区设置 ──────────────────────────────────────────────────────
message_buffer = defaultdict(list)
flush_tasks = {}
suppressed_keys = set()  # 被广告清空后需跳过下一次合并
BUFFER_TIME = 2.0

async def flush_buffer(key):
    """在 BUFFER_TIME 后合并并发送缓存的 Message，然后清理缓存和临时文件。"""
    await asyncio.sleep(BUFFER_TIME)

    # 如果该 key 因广告已被清空，则跳过本次合并
    if key in suppressed_keys:
        logging.info(f"⏭️ 因广告被清空，跳过合并转发 {key}")
        suppressed_keys.discard(key)  # 清除标记
        flush_tasks.pop(key, None)
        message_buffer.pop(key, None)
        return

    msgs = message_buffer.pop(key, [])
    flush_tasks.pop(key, None)
    if not msgs:
        return

    # 合并所有文字
    texts = [m.message.strip() for m in msgs if m.message and m.message.strip()]
    combined_text = "\n".join(texts) if texts else None

    # 打印调试信息，确保 combined_text 里有正确的内容
    logging.debug(f"合并的文本内容：{combined_text}")

    files = []
    for m in msgs:
        if m.media:
            try:
                path = await m.download_media(file='/tmp')
                if path:
                    files.append(path)
            except Exception as e:
                logging.error(f"下载媒体失败: {e}")

    chat = await client.get_entity(key[0])
    title = getattr(chat, "title", str(key[0]))
    username = getattr(chat, "username", "")
    prefix = f"来源：{title}[{username}]\n\n"

    # 确保文本内容不为空并且存在
    if combined_text:
        # combind_text取md5值
        md5_hash = hashlib.md5(combined_text.encode('utf-8')).hexdigest()
        # 从md5.txt文件中读取已发送的md5值
        # 如果md5_hash在文件中，则不发送
        # 如果不在文件中，则发送并将md5_hash写入文件
        try:
            with open(config.md5_file, 'r', encoding='utf-8') as f:
                sent_hashes = f.read().splitlines()
        except FileNotFoundError:
            sent_hashes = []
        if md5_hash in sent_hashes:
            logging.info(f"⏭️ 已发送过的内容，跳过合并转发 {md5_hash}")
            return
        # 如果是新内容，则写入md5.txt
        with open(config.md5_file, 'a', encoding='utf-8') as f:
            f.write(md5_hash + '\n')
        # md5.txt文件保留最近2000行
        with open(config.md5_file, 'r+', encoding='utf-8') as f:
            lines = f.readlines()
            if len(lines) > 2000:
                f.seek(0)
                f.writelines(lines[-2000:])

        # 确保有文件，则发送文件；没有文件时发送文本
        try:
            if files:
                await client.send_file(
                    config.target_channel,
                    files,
                    caption=prefix + combined_text
                )
            else:
                await client.send_message(
                    config.target_channel,
                    prefix + combined_text
                )
            logging.info(f"✔️ 合并转发 {len(msgs)} 条消息，媒体数 {len(files)}")
        except Exception as e:
            logging.error(f"合并转发失败: {e}")

    # 清理本地临时文件
    for f in files:
        try:
            os.remove(f)
        except: 
            pass
# ─────────────────────────────────────────────────────────────────────────────

async def main():
    await client.start()
    logging.info("✅ Client 已启动，准备获取频道实体")

    entities = []
    for ch in config.source_channels:
        try:
            ent = await client.get_entity(ch)
            entities.append(ent)
            logging.info(f"🎯 已获取实体: {ch}")
        except Exception as e:
            logging.error(f"⚠️ 无法获取频道 {ch}: {e}")

    @client.on(events.NewMessage(chats=entities))
    @safe_handler
    async def handler(event):
        m = event.message
        if not (m.message or m.media):
            return

        # —— 计算缓冲 key —— 
        chat = await event.get_chat()
        sender = await event.get_sender()
        key = (chat.id, sender.id)

        text = m.message or ""
        # —— 广告过滤：匹配到即清空并取消合并 —— 
        # 过滤广告关键词，文中有以下内容之一跳过
        ad_keywords = load_keywords("ad_keywords.json")
        for k in ad_keywords:
            if k in text:
                logging.info(f"🚫 广告[{k}]跳过，清空缓冲并取消合并任务 {key}")
                task = flush_tasks.pop(key, None)
                if task:
                    task.cancel()
                message_buffer.pop(key, None)
                suppressed_keys.add(key)  # 只在广告时才加入 suppressed_keys
                return

        # —— 你的原有清洗与替换逻辑 —— 
        text = re.sub(
            r'^(?=.*https?://)(?!.*t\.me).*$', 
            '', text, flags=re.MULTILINE
        )
        # 过滤关键词，行中有以下内容之一删除本行
        del_keywords = load_keywords("keywords.json")
        pattern = re.compile(
            rf'^(?=.*(?:{"|".join(del_keywords)})).*$', 
            re.MULTILINE
        )
        text, cnt = pattern.subn('', text)
        # 如果删除行数超过 7 行，则视为广告，清空缓冲并取消合并任务
        if cnt >= 7:
            return
        text = re.sub(r'\n+', '\n', text).strip()
        for old, new in config.replacements.items():
            text = text.replace(old, new)
        for pat, rep in config.ad_replacements.items():
            text = re.sub(pat, rep, text, flags=re.MULTILINE)

        m.message = text
        message_buffer[key].append(m)

        # 启动或复用定时合并任务
        if key not in flush_tasks:
            flush_tasks[key] = asyncio.create_task(flush_buffer(key))

    logging.info("📡 正在监听多个频道...")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
