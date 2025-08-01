from config_db import init_config_db, set_global_config, set_replacements, set_ad_replacements
import json

init_config_db()

# 全局配置
set_global_config("api_id", "24382238")
set_global_config("api_hash", "a926790195b42a472477e7709a74fc24")
set_global_config("session_name", "/root/telegram_bot/jam16910_session.session")
set_global_config("md5_file", "md5.txt")
set_global_config("ONLY_MEDIA", "False")
set_global_config("bot_username", "@dny9527bot")
set_global_config("BOT_TOKEN", "7651672875:AAHLRyFeC7XepKnohCyusslzYDdzhirZg_c")
set_global_config("BOT_CHANNEL_USERNAME", "@dny9527")
set_global_config("BOT_WELCOME_TEXT", """👋 欢迎使用 📡东南亚曝光台 投稿机器人
曝光🌏各类黑幕与不良事件，直击真相🔍
揭开幕后丑陋面纱，让违规者无处遁形🚨
劲爆爆料持续不断，重磅信息不容错过📢
📢 频道订阅： t.me/@dny9527
投稿要求：
        文案+图（限6张），提供有效证据，
        投稿免费，免费澄清，感谢配合。
有建议或意见可以点击“联系客服”。
""")

# 频道
import sqlite3
conn = sqlite3.connect("config.db")
c = conn.cursor()
c.execute("INSERT INTO channels (type, value) VALUES (?, ?)", ("target", "@dny9527"))
c.execute("INSERT INTO channels (type, value) VALUES (?, ?)", ("review", "-1002871459104"))
c.execute("INSERT INTO channels (type, value) VALUES (?, ?)", ("admin", "-1002871459104"))
for ch in [
    '@ksir_6688','@miandianDS','@tx100','@Spri1te3mr','@bx666','@dj17baoguang','@DYXWTV','@miandian99996',
    '@BG888x','@dnyggg','@DNY_hasj','@kanxia','@MGHDSJ','@cnotc_news','@dongnanyam','@gaojing8888',
    '@CG887','@tx175','@pueee','@ygxw1','@Ru_Yi88','@SJTFLP','@jinbiany','@SJTJPZ','@miandiandashijian168',
    '@miandiande','@kk90690','@bx1OO','@cn_zhm0','@eeollse','@feilvbinya'
]:
    c.execute("INSERT INTO channels (type, value) VALUES (?, ?)", ("source", ch))
conn.commit()
conn.close()

# 管理员ID
set_global_config("ADMIN_IDS", json.dumps([7776592210, 6403012933, 7609694754]))
set_global_config("admin_notify_group", "-1002871459104")

# 替换表和广告表
from config import replacements, ad_replacements
set_replacements(replacements)
set_ad_replacements(ad_replacements)