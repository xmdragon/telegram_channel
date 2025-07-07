from telethon import TelegramClient
import asyncio

api_id = 24382238
api_hash = 'a926790195b42a472477e7709a74fc24'
phone = '+85264854380'
session_name = 'jam16910_session'

async def main():
    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        sent = await client.send_code_request(phone)
        print(f"Telegram 发来了验证码（发送到你的手机）")
        code = input("请输入验证码: ")
        await client.sign_in(phone=phone, code=code, phone_code_hash=sent.phone_code_hash)
        print("✅ 登录成功并生成 session 文件")
    else:
        print("✅ 已经登录，无需再次输入验证码")
    await client.disconnect()

asyncio.run(main())
