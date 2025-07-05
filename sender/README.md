# 🚀 Telegram 多账号自动私信系统

## ✨ 功能概览

### ✅ 多账号并发
- 支持在 `config.yaml` 中配置多个 Telegram 账号（session、api_id、api_hash）。
- 使用 `asyncio.gather` 并行运行：
  - 第 1 个账号用于监听频道关联的讨论群，记录发言用户。
  - 其余账号从数据库轮流获取用户，分摊发私信压力。

---

### ✅ 自动关联频道 & 讨论群
- 读取 `config.yaml` 的 `channels` 链接（如 `https://t.me/xxx`）。
- 自动通过 `GetFullChannelRequest` 找到频道的讨论群。
- 无需手动配置群链接。

---

### ✅ 历史遍历 + 实时监听
- 启动后先遍历所有讨论群成员（`iter_participants`）写入数据库。
- 然后通过 `@client.on(events.NewMessage(...))` 实时监听新发言用户。

---

### ✅ 数据库存储用户信息
在 `sent_users` 表中记录：
| 列名          | 说明                      |
|--------------|--------------------------|
| `user_id`    | Telegram 用户唯一 ID     |
| `username`   | 用户 @ 名称（可为空）    |
| `phone`      | 用户电话（可为空）       |
| `first_name` | 用户名字（可为空）       |
| `last_name`  | 用户姓氏（可为空）       |
| `last_sent_date` | 最后更新时间       |
| `sent_flag`  | 状态：<br>0=未发<br>1=已发<br>-1=隐私/禁止发送 |

并使用：
- `daily_counts` 表记录每天每个账号发信数，控制每日限额。

---

### ✅ 永久避免重复发送
- 只从 `sent_users` 中 `sent_flag=0` 的用户中选择发信。
- 一旦发送成功，更新为 `sent_flag=1`。
- 如果发送出现隐私限制或禁止（包括 `PRIVACY`, `PREMIUM_REQUIRED`, `ChatWriteForbidden` 等），更新为 `sent_flag=-1`，以后永久不再尝试。

---

### ✅ 自动 FloodWait 智能等待
- 遇到 `FloodWaitError`，会自动等待 `seconds+5` 秒继续。
- 完全防止因为短时间大量请求而被限制。

---

### ✅ 支持延迟与平滑随机
- 在 `config.yaml` 中配置：
  ```yaml
  min_delay: 5
  max_delay: 10

## 安装
```bash
pip install -r requirements.txt
```

## 部署后台服务
1️⃣ 用 systemd，写 /etc/systemd/system/sender.service：
``` ini
[Unit]
Description=Telegram Sender Forever
After=network.target

[Service]
ExecStart=/usr/bin/python3 /root/sender_service.py
WorkingDirectory=/root
Restart=always
RestartSec=5
User=root

[Install]
WantedBy=multi-user.target
```
2️⃣ 启动：
``` bash
sudo systemctl daemon-reload
sudo systemctl enable sender.service
sudo systemctl start sender.service
```