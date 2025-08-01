from telethon import TelegramClient
import asyncio
import db

api_id = 24382238
api_hash = 'a926790195b42a472477e7709a74fc24'
client = TelegramClient('../jam16910_session.session', api_id, api_hash)

async def fetch_messages():
    db.init_db()
    conn = db.get_db_connection()
    async for message in client.iter_messages('your_channel_username'):
        if message.text:
            conn.execute('INSERT INTO messages (telegram_id, channel_id, text, date) VALUES (?, ?, ?, ?)',
                         (message.id, message.peer_id.channel_id, message.text, str(message.date)))
            conn.commit()
    conn.close()
    print("✅ All messages saved.")

with client:
    client.loop.run_until_complete(fetch_messages())
