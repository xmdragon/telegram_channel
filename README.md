# 电报采集机器人

## 申请个电报号码
用非大陆电话号码申请个电报号码，开启二步验证
 
## 创建频道
创建一个频道

## 申请API
前往https://my.telegram.org，输入申请电报的电话号码，注意国际区号，输入验证码，登陆后选择“API development tools”，填写App title和Short name即可，会得到API ID 和API HASH。

## 安装telethon
``` bash
# 安装 venv（通常已自带）
sudo apt update
sudo apt install python3-venv python3-pip

# 创建虚拟环境
python3 -m venv venv

# 进入虚拟环境
source venv/bin/activate

# 在虚拟环境中安装 telethon
pip install telethon
```
如果以上出错，可以试试这个
``` bash
pip install --break-system-packages telethon
```

## 采集历史数据（可选）
``` bash
python3 /home/ubuntu/telegram_channel/get_history.py
```
第一次要输入账号信息，之后会在文件下生成my_session.session文件，这个文件一定要保存好，不要给别人知道，不然账号可能有危险！！！

## 启动服务
``` bash
vim /etc/systemed/system/bot.service
```
把以下内容填进去，注意路径
``` ini
[Unit]
Description=My Telegram Bot
After=network.target

[Service]
WorkingDirectory=/home/ubuntu/telegram_channel
ExecStart=/usr/bin/python3 /home/ubuntu/telegram_channel/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
然后执行以下命令
``` bash
sudo systemctl daemon-reload
sudo systemctl enable bot
sudo systemctl start bot
sudo systemctl status bot
```

## 投稿机器人
``` bash
# 1. 安装 venv 支持（若已安装可跳过）
sudo apt update
sudo apt install python3-venv

# 2. 在项目目录下创建并激活虚拟环境
cd /path/to/your/bot
python3 -m venv venv
source venv/bin/activate

# 3. 升级 pip（可选，但推荐）
pip install --upgrade pip

# 4. 安装所需依赖，自动拉取与 PTB 兼容的 urllib3 版本
pip install urllib3==1.26.15
pip install python-telegram-bot SQLAlchemy APScheduler

```
## 投稿机器人服务
### 1. 确定环境与路径

假设你的 Bot 项目放在 /root/telegram_bot/ 目录，虚拟环境在 /root/telegram_bot/venv/，入口脚本是 /root/telegram_bot/post.py。
###　2. 编写 systemd 单元文件

在 /etc/systemd/system/telegram_post.service 中创建并写入：
``` ini
[Unit]
Description=Telegram 投稿机器人
After=network.target

[Service]
Type=simple
User=root
# 如果你想用非 root 账号，改成对应的用户名
WorkingDirectory=/root/telegram_post
# 激活虚拟环境后执行脚本
ExecStart=/root/telegram_bot/venv/bin/python3 /root/telegram_bot/post.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```
注意

    User= 可以改成你的系统普通用户，避免用 root 运行。

    Restart=always 保证脚本意外退出后自动重启。

    RestartSec=5 表示失败后 5 秒重启一次。

### 3. 重新加载 systemd 并启用服务

### 重新加载所有单元文件
``` bash
sudo systemctl daemon-reload
```
### 启动服务并查看状态
``` bash
sudo systemctl start telegram_post
sudo systemctl status telegram_post
```

### 开机自启
``` bash
sudo systemctl enable telegram_post
```

如果 status 显示 running 并且没有错误日志，那么说明你的 Bot 已经作为服务在后台运行，并且会在每次开机时自动启动。
### 4. 管理服务命令

查看日志：
``` bash
sudo journalctl -u telegram_post -f
```
停止服务：
``` bash
sudo systemctl stop telegram_post
```
重启服务：
``` bash
sudo systemctl restart telegram_post
```

## 网页维护广告关键词
``` bash
pip install gunicorn
```
在你的服务器上创建service文件：
``` bash
/etc/systemd/system/flaskapp.service
```
内容为：
``` ini
[Unit]
Description=Flask App Service
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/root/telegram_bot/web

# 如果有虚拟环境，需要把 PATH 改成你的 venv/bin
Environment="PATH=/root/telegram_bot/web/venv/bin"

# 启动 gunicorn 绑定在 0.0.0.0:5000 上
ExecStart=/root/telegram_bot/web/venv/bin/gunicorn \
    --workers 3 \
    --bind 0.0.0.0:5000 \
    wsgi:app

# 如果崩溃，自动重启
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
##🚀 启动 / 重启服务命令
``` bash
sudo systemctl daemon-reload    # 必须在修改 .service 文件后执行
sudo systemctl enable flaskapp # 开机自启
sudo systemctl start flaskapp  # 启动服务
sudo systemctl status flaskapp # 查看状态
```
跟踪日志输出（包括 gunicorn 的 print / logging）：
``` bash
journalctl -u flaskapp -f
```
重启服务（更新代码后用）：
``` bash
sudo systemctl restart flaskapp
```

