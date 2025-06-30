import logging
import json
import re
import config
import functools
import traceback
import asyncio
import os
import glob

session_files = glob.glob("*.session-journal")
for file in session_files:
    print(f"⚠️ 检测到残留锁文件，已删除: {file}")
    os.remove(file)

from logging.handlers import TimedRotatingFileHandler
from telethon import TelegramClient

# ============= safe_handler 装饰器（暂不用事件回调，保留以后可用） ==============
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

# ==================== JSON 日志配置 ====================
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

# ==================== 主采集逻辑 ====================
async def main():
    client = TelegramClient(config.session_name, config.api_id, config.api_hash)
    await client.start()
    logging.info("🚀 已启动 TelegramClient...")

    for ch_name in config.source_channels:
        logging.info(f'📥 正在采集频道: {ch_name}')
        try:
            channel = await client.get_entity(ch_name)
            async for message in client.iter_messages(channel, limit=100):
                msg = message
                text = msg.message or ''

                # 🚫 跳过广告页
                matched = next((k for k in config.AD_KEYWORDS if k in text), None)
                if matched:
                    logging.info(f"🚫 广告[{matched}]跳过: {text}")
                    continue  # 这里要 continue 只跳过本条

                # 先删除含有 http(s):// 但不含 t.me 的整行
                text = re.sub(
                    r'^(?=.*https?://)(?!.*t\.me).*$', 
                    '', 
                    text, 
                    flags=re.MULTILINE
                )

                # 再删除含有典型广告关键词的行
                pattern_str = '|'.join(config.KEYWORDS)
                pattern = re.compile(
                    rf'^(?=.*(?:{pattern_str})).*$',
                    re.MULTILINE
                )
                text, match_count = pattern.subn('', text)
                # 多次匹配，判定为广告，跳过
                if match_count >= 7:
                    continue
                logging.info(f"🚀广告匹配次数：{match_count}")

                # 再清理多余的空行
                text = re.sub(r'\n+', '\n', text).strip()

                # 过滤替换
                for old, new in config.replacements.items():
                    if text:
                        text= text.replace(old, new)
                for pattern, replacement in config.ad_replacements.items():
                    if text:
                        text = re.sub(pattern, replacement, text, flags=re.MULTILINE)

                # 拼接来源
                channel_title = channel.title or '未知'
                channel_username = channel.username or '无短链'
                channel_info = f'来源：{channel_title}[{channel_username}]\n\n'
                text = channel_info + text

                # ✅ 实际转发
                target_channel = config.target_channel
                await client.send_message(
                    target_channel,
                    text,
                    file=msg.media
                )
                
                logging.info(f"✔️ 已转发: {text}")

                # 采集一条休息一下
                sleep_time = 30
                logging.info("⏳ 累死了，休息 {sleep_time} 秒后再开始...")
                await asyncio.sleep(sleep_time)

        except Exception as e:
            logging.error(f"🚨 采集频道 {ch_name} 出错: {e}\n{traceback.format_exc()}")


# ==================== 启动入口 ====================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("🛑 收到中断信号，退出程序")
    except Exception as e:
        logging.error(f"🚨 主循环异常: {e}\n{traceback.format_exc()}")
