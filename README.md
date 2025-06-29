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
apt install python3-venv

# 创建虚拟环境
python3 -m venv myenv

# 进入虚拟环境
source myenv/bin/activate

# 在虚拟环境中安装 telethon
pip install telethon
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