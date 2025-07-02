import config
import warnings
import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.request import HTTPXRequest
from telegram.error import Conflict

# 静音 httpx INFO 日志
logging.getLogger("httpx").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=UserWarning)

# logging 配置
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# /start：欢迎信息 + 按钮和回复键盘
def start_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("订阅频道", url=f"https://t.me/{config.BOT_CHANNEL_USERNAME.strip('@').lower()}"),
            InlineKeyboardButton("联系客服", url=f"https://t.me/{config.channel_info.author.strip('@')}")
        ]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        config.BOT_WELCOME_TEXT,
        reply_markup=start_markup()
    )
    await update.message.reply_text(
        "请选择操作：",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("开始投稿"), KeyboardButton("完成投稿")]],
            resize_keyboard=True
        )
    )

# submit：开始投稿
def get_submit_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("开始投稿"), KeyboardButton("完成投稿")]],
        resize_keyboard=True
    )

async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["pending"] = []
    context.chat_data["submitting"] = True
    await update.message.reply_text(
        "✅ 已进入投稿模式，请连续发送文字、图片或视频。完成后点击“完成投稿”或输入 /done 。",
        reply_markup=get_submit_keyboard()
    )

# done：结束投稿并预览给管理员
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = context.chat_data
    if not data.get("submitting"):
        await update.message.reply_text("⚠️ 请先开始投稿(点击“开始投稿”或 /submit)。")
        return
    pending = data.get("pending", [])
    if not pending:
        await update.message.reply_text("⚠️ 尚未发送任何内容，无法提交。")
        return
    # 关闭模式并清空键盘
    data["submitting"] = False
    await update.message.reply_text(
        "✅ 投稿已提交给管理员审核。",
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True)
    )

    # 构造审核按钮
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ 发布", callback_data="approve"),
        InlineKeyboardButton("🚫 拒绝", callback_data="reject"),
    ]])
    first = pending[0]
    uname = first.from_user.username or user.username or "无名"

    # 向所有 admin 发送预览标题
    for admin_id in config.ADMIN_IDS:
        try:
            msg = await context.bot.send_message(
                chat_id=admin_id,
                text=f"收到投稿 @{uname}",
                reply_markup=kb
            )
            logger.info(f"向管理员 {admin_id} 发送预览标题，message_id={msg.message_id}")
        except Exception as e:
            logger.error(f"发送给管理员 {admin_id} 标题失败", exc_info=e)

    # 收集并发送内容：先媒体再文字
    texts, media = [], []
    for m in pending:
        if m.text: texts.append(m.text)
        if m.caption: texts.append(m.caption)
        if m.photo: media.append(InputMediaPhoto(m.photo[-1].file_id))
        if m.video: media.append(InputMediaVideo(m.video.file_id))
    # 发送媒体和文字给所有 admin
    for admin_id in config.ADMIN_IDS:
        if media:
            try:
                msgs = await context.bot.send_media_group(chat_id=admin_id, media=media)
                logger.info(f"向管理员 {admin_id} 发送媒体, count={len(msgs)}")
            except Exception as e:
                logger.error(f"media_group 发送给管理员 {admin_id} 失败", exc_info=e)
        if texts:
            combined = "\n\n".join(texts) + f"\n\n#投稿 via @{config.BOT_CHANNEL_USERNAME.strip('@')}"
            try:
                msg = await context.bot.send_message(chat_id=admin_id, text=combined)
                logger.info(f"向管理员 {admin_id} 发送文字, message_id={msg.message_id}")
            except Exception as e:
                logger.error(f"文字发送给管理员 {admin_id} 失败", exc_info=e)

# collect：收集投稿内容
async def collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.chat_data.get("submitting"):
        context.chat_data.setdefault("pending", []).append(update.message)

# handle_callback：管理员审核回调
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pending = context.chat_data.pop("pending", [])
    context.chat_data.pop("submitting", None)
    action = query.data
    texts, media = [], []
    for m in pending:
        if m.text: texts.append(m.text)
        if m.caption: texts.append(m.caption)
        if m.photo: media.append(InputMediaPhoto(m.photo[-1].file_id))
        if m.video: media.append(InputMediaVideo(m.video.file_id))
    if action == "approve":
        # 发布到频道
        if media:
            await context.bot.send_media_group(chat_id=config.BOT_CHANNEL_USERNAME, media=media)
        if texts:
            combined = "\n\n".join(texts) + f"\n\n#投稿 via @{config.BOT_CHANNEL_USERNAME.strip('@')}"
            await context.bot.send_message(chat_id=config.BOT_CHANNEL_USERNAME, text=combined)
        await query.edit_message_text("✅ 已发布到频道。")
    else:
        await query.edit_message_text("🚫 投稿已拒绝。")

# pingadmin：测试管理员连通
async def pingadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text="✅ Bot 通知成功")
        except Conflict:
            logger.warning(f"pingadmin 冲突, admin={admin_id}")
    await update.message.reply_text("✅ 测试消息已发送给所有管理员。")

# 全局错误处理
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    err = context.error
    if isinstance(err, Conflict):
        logger.warning("Conflict 刷新轮询冲突，继续执行。")
        return
    logger.error("未处理异常：", exc_info=err)

# 启动
if __name__ == "__main__":
    logger.info(f"ADMIN_IDS={config.ADMIN_IDS}")
    req = HTTPXRequest(connect_timeout=5.0, read_timeout=20.0)
    app = Application.builder() \
        .token(config.BOT_TOKEN) \
        .build()
    # 注册 handlers
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("submit", submit))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(MessageHandler(filters.Regex("^(开始投稿)$"), submit))
    app.add_handler(MessageHandler(filters.Regex("^(完成投稿)$"), done))
    app.add_handler(CommandHandler("pingadmin", pingadmin))
    app.add_handler(MessageHandler(filters.ALL, collect))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot running...")
    app.run_polling(drop_pending_updates=True)
