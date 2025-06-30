from types import SimpleNamespace
import json

# API 信息
api_id = 20994599
api_hash = '443ee1e0161f6bb3f358fd4966cc5587'
session_name = '/root/telegram_bot/my_session.session'

# ========================
# 目标频道
# 如：@mychannel 或 -1001234
# ========================
target_channel = 'https://t.me/bigeventsinsea'

# 替换关键字
# 替换映射表
channel_info = SimpleNamespace(    
    title = '🔔 订阅东南亚大事件「曝光」',
    url = '🔗  t.me/bigeventsinsea',
    short_url = 'bigeventsinsea',
    contact = '☎️ 投稿曝料：@stan0505',
    author = '＠stan0505'
)

# @SEABigEvents_2025_bot
# 你的机器人token
BOT_TOKEN = '7905520524:AAF2NAh4vcJ24TbdnNhKb5QS8EeWN__xin8'
# 你的 Telegram 用户 ID（整数）
ADMINS = [
    7776592210
]
# 你的频道 username
BOT_CHANNEL_USERNAME = '@bigeventsinsea'

# ========================
# 源频道列表
# 只能用 @username
# ========================
source_channels = [
    '@miandianDS',
    '@pueee',
    '@Spri1te3mr',
    '@bx666',
    '@DNYba',
    '@dj17baoguang',
    '@DYXWTV',
    '@miandian99996',
    '@BG888x',
    '@dnyggg',
    '@DNY_hasj',
    '@ygxw1',
    '@kanxia',
    '@MGHDSJ',
    '@cnotc_news',
    '@dongnanyam',
    '@gaojing8888',
    '@CG887',
    '@cn789',
    '@MGHDSJ',
    '@ksir_6688'
]

# 是否只转发含媒体的消息
ONLY_MEDIA = False  # True 表示只转发有图片/视频的消息

replacements = {
    # https://t.me/tx100
    # https://t.me/dongnanya0027
    '🔗 https://t.me/dongnanya0027': channel_info.url,
    '☎️ 投稿澄清爆料：@DNW8888': channel_info.contact,
    '🔔订阅东南亚大事件曝光-聚焦时事': channel_info.title,


    # https://t.me/DNYba
    '🔗https://t.me/dnyba': channel_info.url,
    '☎️免费爆料 🥰广告合作：@FKabc': channel_info.contact,
    '🔔订阅东南亚大事件频道': channel_info.title,

    # https://t.me/pueee
    # https://t.me/pyzxw
    # https://t.me/pyzcc
    # https://t.me/pyzbg
    '🔗 t.me/+UNWEBNeUmh84MDVl': channel_info.url,
    '😍 投稿爆料联系：@Pyz22': channel_info.contact,
    '🔔订阅东南亚大事件': channel_info.title,
    '✅ 消息已收录到 @soso': '',

    # https://t.me/Spri1te3mr
    '\n🔍订阅&柬埔寨新闻/东南亚大事件 (https://t.me/Spri1te3mr)': channel_info.title,
    '\n🔍投稿爆料商务合作找小柚子 (https://t.me/xyz662)💙': channel_info.url,
    '\n🔍全球线上线下人工翻译找小柚子 (https://t.me/xyz662)🍒': channel_info.contact,

    # https://t.me/bx666
    # https://t.me/okdb
    # https://t.me/bx555
    # https://t.me/tx177
    # https://t.me/tx174
    '🔗 t.me/+Rg10ttQa0odkYzc1': channel_info.url,
    '😍投稿澄清爆料： @tx188': channel_info.contact,
    '📣 订阅东南亚大事件频道  ↓': channel_info.title,

    # https://t.me/miandianDS
    '🔗 https://t.me/miandianDS': channel_info.url,
    '😍投稿澄清爆料： @QianQian106': channel_info.contact,
    '📣 订阅东南亚大事件频道  ↓': channel_info.title,

    # https://t.me/dj17baoguang
    '➡️曝光频道：@dj17baoguang': channel_info.title,
    '➡️听歌频道：@dj17': channel_info.url,
    '➡️重大爆料：@dj17remix': channel_info.contact,

    # https://t.me/DYXWTV
    '🔗  https://t.me/+VtJtheQY1VY1ZDc1': channel_info.url,
    '📩免费投稿爆料： @WXN66': channel_info.contact,
    '🔔订阅【第一新闻】博彩-灰产从业者必备品': channel_info.title,

    # https://t.me/miandian99996
    '✉️投稿联系：@huazai37': channel_info.title + "\n" + channel_info.url + "\n" + channel_info.contact,

    # https://t.me/BG888x
    # https://t.me/xpppp
    # https://t.me/haiwaixinwen
    # https://t.me/bg1111
    # https://t.me/dny_bg
    # https://t.me/baoguangpaolu
    '🔔东南亚曝光（吃瓜）群     @XPPPP': channel_info.title + "\n" + channel_info.url,
    '🔥发布悬赏/招商请联系： @FFFTG': channel_info.contact,

    # https://t.me/tx175
    '🔵91奇趣吃瓜🍉': channel_info.title,
    '😍订阅：@tx175 (http://t.me/+4qNglxzXfg5iNzBl)': channel_info.url,
    '😍trx能量：@trx523 (https://t.me/+X-RzESb5IJhkYmU1)': channel_info.contact,

    # https://t.me/dnyggg
    # https://t.me/Tequxuanshang
    '📣关注东南亚悬赏-吃瓜中心': channel_info.title,
    '🍉：91奇趣吃瓜 @tx175\n': '',
    '🔋Trx能量手续费兑换 @Trx523': channel_info.url,
    '💬 欢迎投稿爆料： @BG770': channel_info.contact,

    # https://t.me/DNY_hasj
    '👌订阅频道： @DNY_hasj': channel_info.title,
    '👌投稿爆料： @molu136': channel_info.url,
    '👌海外交友： @haiwai_JLB': channel_info.contact,

    # https://t.me/ygxw1
    # https://t.me/ygxw2
    # https://t.me/ygxw3
    # https://t.me/ygxw4
    # https://t.me/ygxw5
    # https://t.me/ygxw6
    # https://t.me/ygxw7
    # https://t.me/ygxw8
    # https://t.me/ygxw9
    # https://t.me/ygxw10
    # https://t.me/ygxw88
    '🔔 订阅亚太新闻频道  ↓': channel_info.title,
    '🔗 t.me/+cc29sJCYychlYzhl': channel_info.url,
    '☎️ 欢迎爆料： @yt1338': channel_info.contact,
    '🥇 (https://t.me/yt1888)亚太导航 (https://t.me/yt18B)🎖 (https://t.me/yt1888)亚太吃瓜 (https://t.me/yt7733)🥇 (https://t.me/yt1125)二手市场 (https://t.me/yatai1358)': '',

    # https://t.me/kanxia
    # https://t.me/dnydsj
    '🔗  t.me/+bSG_NNJH-_83MTRl': channel_info.url,
    '😍 订阅东南亚大事件频道  ↓': channel_info.title,
    '😀  西瓜皮淘气包：@xgptqb': channel_info.contact,


    # https://t.me/MGHDSJ
    '✅东南亚闯荡纪频道订阅': channel_info.title,
    '链接:https://t.me/MGHDSJ': channel_info.url,
    '♾东南亚闯荡纪免费曝料\n': '',
    '投稿:@CJH13790': channel_info.contact,

    # https://t.me/dongnanyam
    ' (https://333367.vip/)频道广告赞助商': '',
    '🔔 订阅东南亚大事件频道↓↓↓': channel_info.title,
    '🔗 t.me/+qA-vTHkRMZk3N2M1': channel_info.url,
    '☎️ 欢迎投稿爆料：@Bnnc888': channel_info.contact,

    # https://t.me/gaojing8888
    '🔔 订阅东南亚头条新闻频道  ↓': channel_info.title,
    '🔗 https://t.me/gaojing8888': channel_info.url,
    '☎️ 免费投稿/爆料：@zqq3333': channel_info.contact,
    '\n✈️代开飞机会员：@zqq3333': '',
    '\n💻商务广告合作：@zqq3333': '',

    # https://t.me/cn789
    # https://t.me/cgtn88
    # https://t.me/cgtn110
    # https://t.me/miandian_xinwen
    '☎️投稿联系： @shuaibi\n': channel_info.title + "\n" + channel_info.url + "\n",
    '📩缅北吃瓜： @mianbei119': channel_info.contact,

    # https://t.me/MGHDSJ
    '✅东南亚闯荡纪频道订阅': channel_info.title,
    '链接:https://t.me/MGHDSJ': channel_info.url,
    '♾东南亚闯荡纪免费曝料\n': '',
    '投稿:@CJH13790': channel_info.contact,

    # https://t.me/cnotc_news
    # https://t.me/PG134
    '💥 点击投稿爆料 (http://t.me/fou996) 分享你的酸甜苦辣吧~~~\n': '',
    '❤️ 订阅东南亚闯荡记频道👇': channel_info.title,
    '🔗 t.me/+jubfEE6e1zphODA9': channel_info.url,
    '❤️ 欢迎投稿爆料：@fou996': channel_info.contact
}

# 广告过滤列表
ad_replacements = {
    r'———————————————[\s\S]*?———————————————': '',
    r'频道广告赞助商[\s\S]*?\(https:\/\/t.me\/MKFT168\)': '',
    r'^.*亚太导航.*\n?': '',
    r'^.*查档开户.*\n?': '',
    r'.*视频传送门.*\n?': '',
    r'^.*本消息[\d]+秒后自动删除.*\n?': ''
}