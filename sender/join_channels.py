import asyncio
import yaml
from telethon import TelegramClient
from telethon.errors import UserAlreadyParticipantError, FloodWaitError, ChatAdminRequiredError
from telethon.tl.functions.channels import JoinChannelRequest
import re
import time
import random

# 文件路径
URL_FILE = "url.txt"
CONFIG_FILE = "config.yaml"

def load_accounts(config_file):
    with open(config_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)["accounts"]

def load_channels(url_file):
    with open(url_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    channels = []
    for line in lines:
        line = line.strip()
        # 提取 t.me/xxx 中的 xxx
        match = re.search(r"(?:t\.me/)?([a-zA-Z0-9_]+)", line)
        if match:
            channels.append(match.group(1))
    return list(set(channels))  # 去重

async def join_channels(account, channels):
    client = TelegramClient(account["session"], account["api_id"], account["api_hash"])
    await client.start()
    me = await client.get_me()
    print(f"🚀 [{me.first_name}] 登录成功，开始加入频道...")

    for channel in channels:
        try:
            await client(JoinChannelRequest(channel))
            print(f"✅ 加入频道: {channel}")
            # 等待5到10秒以避免过快请求
            await asyncio.sleep(random.uniform(5, 10))
        except UserAlreadyParticipantError:
            print(f"⚠️ 已在频道: {channel}")
        except FloodWaitError as e:
            print(f"⏳ FloodWait: 等待 {e.seconds} 秒后继续...")
            time.sleep(e.seconds)
        except ChatAdminRequiredError:
            print(f"🚫 没有权限加入: {channel}")
        except Exception as e:
            print(f"❌ 加入频道失败: {channel}, 错误: {e}")
    await client.disconnect()

async def main():
    accounts = load_accounts(CONFIG_FILE)
    channels = load_channels(URL_FILE)
    print(f"📋 共加载 {len(channels)} 个频道")

    for account in accounts:
        await join_channels(account, channels)
        print(f"🌙 账号 {account['session']} 已完成加入。")

if __name__ == "__main__":
    asyncio.run(main())