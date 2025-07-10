# 电报机器人

## 申请个电报号码
用非大陆电话号码申请个电报号码，开启二步验证
 
## 创建频道
创建一个频道

## 申请API
前往https://my.telegram.org，输入申请电报的电话号码，注意国际区号，输入验证码，登陆后选择“API development tools”，填写App title和Short name即可，会得到API ID 和API HASH。

## 1、采集机器人
### 1. 安装telethon
``` bash
# 安装 venv
sudo apt update
sudo apt install python3-venv python3-pip

# 在项目目录下创建并激活虚拟环境
cd /root/telegram_bot
python3 -m venv venv
source venv/bin/activate

# 在虚拟环境中安装 telethon
pip install telethon
```

### 采集历史数据（可选）
``` bash
python3 /root/telegram_bot/get_history.py
```
第一次要输入账号信息，之后会在文件下生成*.session文件，这个文件一定要保存好，不要给别人知道，不然账号可能有危险！！！

### 2. 编写 systemd 单元文件
在 /etc/systemed/system/bot.service 中创建并写入：
``` ini
[Unit]
Description=Telegram 采集脚本
After=network.target

[Service]
WorkingDirectory=/root/telegram_bot
ExecStart=/root/telegram_bot/venv/bin/python3 /root/telegram_bot/bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

#### 重新加载所有单元文件
``` bash
sudo systemctl daemon-reload
```
#### 开机自启
``` bash
sudo systemctl enable telegram_bot
```
#### 启动服务并查看状态
``` bash
sudo systemctl start telegram_bot
sudo systemctl status telegram_bot
```

## 2、投稿机器人
### 1. 安装python-telegram-bot
``` bash
# 安装 venv
sudo apt update
sudo apt install python3-venv

# 在项目目录下创建并激活虚拟环境
cd /root/telegram_bot
python3 -m venv venv
source venv/bin/activate


# 在虚拟环境中安装 python-telegram-bot
# 安装所需依赖，自动拉取与 PTB 兼容的 urllib3 版本
pip install urllib3==1.26.15
pip install python-telegram-bot SQLAlchemy APScheduler

```

### 2. 编写 systemd 单元文件
在 /etc/systemd/system/telegram_post.service 中创建并写入：
``` ini
[Unit]
Description=Telegram 投稿机器人
After=network.target

[Service]
Type=simple
User=root

WorkingDirectory=/root/telegram_bot
ExecStart=/root/telegram_bot/venv/bin/python3 /root/telegram_bot/post.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

### 3. 重新加载 systemd 并启用服务

### 重新加载所有单元文件
``` bash
sudo systemctl daemon-reload
```
### 开机自启
``` bash
sudo systemctl enable telegram_post
```
### 启动服务并查看状态
``` bash
sudo systemctl start telegram_post
sudo systemctl status telegram_post
```

## 3、广告关键词维护
### 1. 安装gunicorn
``` bash
# 安装 venv
sudo apt update
sudo apt install python3-venv python3-pip

# 在项目目录下创建并激活虚拟环境
cd /root/telegram_bot
python3 -m venv venv
source venv/bin/activate

# 在虚拟环境中安装 telethon
pip install gunicorn
```
### 2. 编写 systemd 单元文件
在 /etc/systemd/system/telegramflaskapp.service 中创建并写入：
``` ini
[Unit]
Description=广告关键词维护
After=network.target

[Service]
type=simple
User=root
WorkingDirectory=/root/telegram_bot/web

Environment="PATH=/root/telegram_bot/web/venv/bin"
ExecStart=/root/telegram_bot/web/venv/bin/gunicorn \
    --workers 3 \
    --bind 0.0.0.0:5000 \
    wsgi:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
### 3. 重新加载 systemd 并启用服务

### 重新加载所有单元文件
``` bash
sudo systemctl daemon-reload
```
### 开机自启
``` bash
sudo systemctl enable flaskapp
```
### 启动服务并查看状态
``` bash
sudo systemctl start flaskapp
sudo systemctl status flaskapp
```