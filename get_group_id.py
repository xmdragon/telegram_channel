
# get_chat_id.py
from telethon import TelegramClient, events
import config
import asyncio

client = TelegramClient(config.session_name, config.api_id, config.api_hash)

@client.on(events.NewMessage)
async def handler(event):
    chat = await event.get_chat()
    print(f"在 【{chat.title}】 收到消息，chat_id={event.chat_id}")

async def main():
    await client.start()
    print("✅ 已启动，发消息到你想获取 ID 的群即可")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
