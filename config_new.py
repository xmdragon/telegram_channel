from types import SimpleNamespace
import json
from config_db import (
    get_global_config, get_channels, get_replacements, get_ad_replacements
)

# API 信息
api_id = int(get_global_config("api_id"))
api_hash = get_global_config("api_hash")
session_name = get_global_config("session_name")

# 目标频道
target_channel = get_channels("target")[0]

# 替换关键字
channel_info = SimpleNamespace(
    title = '🔔 订阅📡东南亚曝光台',
    url = f'🔗  t.me/{target_channel.strip("@")}',
    short_url = f'{target_channel.strip("@")}',
    contact = '☎️ 投稿曝料：@stan0505',
    author = '@stan0505'
)

# 审核群ID
review_groups = [int(x) if x.startswith('-') else x for x in get_channels("review")]
admin_notify_group = int(get_global_config("admin_notify_group"))

# 多个管理员 ID 列表
ADMIN_IDS = json.loads(get_global_config("ADMIN_IDS"))

bot_username = get_global_config("bot_username")
BOT_TOKEN = get_global_config("BOT_TOKEN")
BOT_CHANNEL_USERNAME = get_global_config("BOT_CHANNEL_USERNAME")
BOT_WELCOME_TEXT = get_global_config("BOT_WELCOME_TEXT")

# 源频道列表
source_channels = get_channels("source")

# 是否只转发含媒体的消息
ONLY_MEDIA = get_global_config("ONLY_MEDIA") == "True"

replacements = get_replacements()
ad_replacements = get_ad_replacements()

md5_file = get_global_config("md5_file")