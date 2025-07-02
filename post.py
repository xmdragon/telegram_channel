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
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 欢迎文本
    await update.message.reply_text(config.BOT_WELCOME_TEXT,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("订阅频道", url=f"https://t.me/{config.BOT_CHANNEL_USERNAME.strip('@').lower()}"),
                InlineKeyboardButton("联系客服", url=f"https://t.me/{config.channel_info.author.strip('@')}")
            ]
        ])
    )
    # 底部回复键盘
    await update.message.reply_text("请选择操作：",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("开始投稿"), KeyboardButton("完成投稿")]],
            resize_keyboard=True,
        )
    )

# submit：开始投稿
async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["pending"] = []
    context.chat_data["submitting"] = True
    # 引导文本
    await update.message.reply_text(
        "✅ 已进入投稿模式，请连续发送文字、图片或视频。完成后点击“完成投稿”或输入 /done 。"
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
    await update.message.reply_text("✅ 投稿已提交给管理员审核。", reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))

    # 构造审核按钮
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ 发布", callback_data="approve"),
        InlineKeyboardButton("🚫 拒绝", callback_data="reject"),
    ]])
    first = pending[0]
    uname = first.from_user.username or user.username or "无名"
    try:
        msg = await context.bot.send_message(chat_id=config.ADMIN_ID,
            text=f"收到投稿 @{uname}",
            reply_markup=kb
        )
        logger.info(f"审核标题发出，message_id={msg.message_id}")
    except Exception as e:
        logger.error("发送审核标题失败", exc_info=e)
        await update.message.reply_text("⚠️ 无法通知管理员。")
        return

    # 收集并发送内容：先媒体再文字
    texts, media = [], []
    for m in pending:
        if m.text: texts.append(m.text)
        if m.caption: texts.append(m.caption)
        if m.photo: media.append(InputMediaPhoto(m.photo[-1].file_id))
        if m.video: media.append(InputMediaVideo(m.video.file_id))
    if media:
        try:
            msgs = await context.bot.send_media_group(chat_id=config.ADMIN_ID, media=media)
            logger.info(f"media_group sent {len(msgs)} media")
        except Exception as e:
            logger.error("media_group发送失败", exc_info=e)
    if texts:
        combined = "\n\n".join(texts) + f"\n\n#投稿 via @{config.BOT_CHANNEL_USERNAME.strip('@')}"
        try:
            msg = await context.bot.send_message(chat_id=config.ADMIN_ID, text=combined)
            logger.info(f"文字内容发送成功，message_id={msg.message_id}")
        except Exception as e:
            logger.error("文字内容发送失败", exc_info=e)

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
    try:
        await update.message.reply_text("✅ 测试完成。")
        await context.bot.send_message(chat_id=config.ADMIN_ID, text="✅ Bot 通知成功")
    except Conflict:
        logger.warning("pingadmin冲突，忽略")
        await update.message.reply_text("⚠️ 测试通知冲突，可能已有实例在运行。")

# 全局错误处理
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    err = context.error
    if isinstance(err, Conflict):
        logger.warning("Conflict 刷新轮询冲突，继续执行。")
        return
    logger.error("未处理异常：", exc_info=err)

# 启动
def main():
    logger.info(f"ADMIN_ID={config.ADMIN_ID} (type={type(config.ADMIN_ID)})")
    req = HTTPXRequest(connect_timeout=5.0, read_timeout=20.0)
    app = Application.builder() \
        .token(config.BOT_TOKEN) \
        .request(req) \
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

    logger.info("Bot running...，使用 drop_pending_updates")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()