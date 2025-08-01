from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
import db
from telethon import TelegramClient
import asyncio

app = Flask(__name__)
CORS(app)
app.config["JWT_SECRET_KEY"] = "admin-secret-key"  # 生产请用更安全的
jwt = JWTManager(app)

api_id = 123456
api_hash = 'YOUR_API_HASH'
client = TelegramClient('session/my_session', api_id, api_hash)

# ---------------------
# 登录
# ---------------------
@app.route('/api/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    if username == 'admin' and password == '123456':  # 可改成 DB 校验
        token = create_access_token(identity=username)
        return jsonify(access_token=token)
    return jsonify({"msg": "Bad credentials"}), 401

# ---------------------
# 需要登录的接口
# ---------------------
@app.route('/api/messages')
@jwt_required()
def get_messages():
    conn = db.get_db_connection()
    rows = conn.execute('SELECT * FROM messages ORDER BY id DESC').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/message/<int:id>', methods=['PUT'])
@jwt_required()
def edit_message(id):
    new_text = request.json['text']
    conn = db.get_db_connection()
    row = conn.execute('SELECT telegram_id, channel_id FROM messages WHERE id = ?', (id,)).fetchone()
    if row:
        conn.execute('UPDATE messages SET text=?, edited=1 WHERE id=?', (new_text, id))
        conn.commit()
        asyncio.run(client.edit_message(int('-100'+str(row['channel_id'])), row['telegram_id'], new_text))
    conn.close()
    return jsonify({"status": "ok"})

@app.route('/api/message/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_message(id):
    conn = db.get_db_connection()
    row = conn.execute('SELECT telegram_id, channel_id FROM messages WHERE id = ?', (id,)).fetchone()
    if row:
        asyncio.run(client.delete_messages(int('-100'+str(row['channel_id'])), [row['telegram_id']]))
        conn.execute('DELETE FROM messages WHERE id=?', (id,))
        conn.commit()
    conn.close()
    return jsonify({"status": "deleted"})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5100, debug=True)
