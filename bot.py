import logging
import json
import re
import config
import functools
import traceback

from logging.handlers import TimedRotatingFileHandler
from telethon import TelegramClient, events

def safe_handler(func):
    @functools.wraps(func)
    async def wrapper(event, *args, **kwargs):
        try:
            await func(event, *args, **kwargs)
        except Exception as e:
            # 尝试取出最大量信息
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

# JSON 日志配置
logger = logging.getLogger()
logger.setLevel(logging.INFO)
handler = TimedRotatingFileHandler("bot.log", when="midnight", interval=1, backupCount=30, encoding='utf-8')
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

client = TelegramClient(config.session_name, config.api_id, config.api_hash)

@client.on(events.NewMessage(chats=config.source_channels))
@safe_handler
async def handler(event):
    msg = event.message

    # 🚫 跳过广告关键词
    #if any(k in msg.message for k in config.KEYWORDS):
    #    logging.info(f"🚫 广告[{k}]跳过: {msg.message}")
    #    return
    for k in config.KEYWORDS:
        if k in msg.message:
            logging.info(f"🚫 广告[{k}]跳过: {msg.message}")
            return

    # 过滤关键字替换
    for old, new in config.replacements.items():
        msg.message = msg.message.replace(old, new)
    # 过滤顽固关键字
    for pattern, replacement in config.ad_replacements.items():
        msg.message = re.sub(pattern, replacement, msg.message, flags=re.MULTILINE)

    # 测试期间加入来源地，好对比数据
    channel = await event.get_chat()
    channel_title = channel.title or '未知'
    channel_username = channel.username or '无短链'
    channel_info = '来源：' + channel_title + '[' + channel_username + ']\n'
    
    msg.message = channel_info + msg.message

    # ✅ 重新发送
    await client.send_message(
        config.target_channel,
        msg.message,
        file=msg.media
    )

    logging.info(f"✔️ 已转发: {msg.message}")

client.start()
print("📡 正在监听多个频道...")
client.run_until_disconnected()