import config
import asyncio
from telethon import TelegramClient

async def main():
    client = TelegramClient(config.session_name, config.api_id, config.api_hash)
    await client.start()

    channel_input = input("请输入频道用户名或链接（例如 @yourchannel 或 https://t.me/yourchannel）: ").strip()
    entity = await client.get_entity(channel_input)
    channel_id = entity.id
    full_id = f"-100{channel_id}"  # Telegram 的频道通常需要这样格式

    print(f"频道标题: {entity.title}")
    print(f"频道数字 ID: {full_id}")

    await client.disconnect()

asyncio.run(main())
