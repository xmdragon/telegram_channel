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
from telegram import Update as TgUpdate
from telegram.request import HTTPXRequest
from telegram.error import Conflict

logging.getLogger("httpx").setLevel(logging.WARNING)
warnings.filterwarnings("ignore", category=UserWarning)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        config.BOT_WELCOME_TEXT
    )
    # -- 这里改成 InlineKeyboard --
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("开始投稿", callback_data="start_submit"),
        InlineKeyboardButton("完成投稿", callback_data="finish_submit"),
    ]])
    await update.message.reply_text(
        "请选择操作：",
        reply_markup=keyboard
    )

async def inline_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # 点击“开始投稿”
    if query.data == "start_submit":
        # 构造一个新的 Update，把 query.message 当作 message
        fake_update = TgUpdate(
            update_id=update.update_id,
            message=query.message
        )
        await submit(fake_update, context)

    # 点击“完成投稿”
    elif query.data == "finish_submit":
        fake_update = TgUpdate(
            update_id=update.update_id,
            message=query.message
        )
        await done(fake_update, context)

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

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = context.chat_data
    if not data.get("submitting"):
        await update.message.reply_text("⚠️ 请先开始投稿。")
        return
    pending = data.get("pending", [])
    if not pending:
        await update.message.reply_text("⚠️ 尚未发送任何内容，无法提交。")
        return

    # 关闭投稿模式
    data["submitting"] = False
    await update.message.reply_text("✅ 投稿已提交给管理员审核。",
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))

    # 收集文本和媒体
    texts, media = [], []
    for m in pending:
        if m.text: texts.append(m.text)
        if m.caption: texts.append(m.caption)
        if m.photo: media.append(InputMediaPhoto(m.photo[-1].file_id))
        if m.video: media.append(InputMediaVideo(m.video.file_id))
    combined_text = "\n\n".join(texts) + f"\n\n#投稿 via @{config.BOT_CHANNEL_USERNAME.strip('@')}"

    # 给每个 admin 发预览标题，并存储 pending 到 bot_data
    for admin_id in config.ADMIN_IDS:
        try:
            # 1) 先发一个纯文本消息，拿到 message_id
            msg = await context.bot.send_message(chat_id=admin_id, text=f"收到投稿 @{user.username or '无名'}")
            logger.info(f"向管理员 {admin_id} 发送预览标题，message_id={msg.message_id}")

            # 2) 存储 pending 列表到全局 bot_data
            key = f"pending_{admin_id}_{msg.message_id}"
            context.bot_data[key] = pending.copy()

            # 3) 编辑这条消息，加上带 message_id 的按钮
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ 发布", callback_data=f"approve:{msg.message_id}"),
                InlineKeyboardButton("🚫 拒绝", callback_data=f"reject:{msg.message_id}")
            ]])
            await context.bot.edit_message_reply_markup(
                chat_id=admin_id,
                message_id=msg.message_id,
                reply_markup=kb
            )
        except Exception as e:
            logger.error(f"给管理员 {admin_id} 发送预览失败", exc_info=e)
            continue

        # 4) 发真实内容给 admin（和之前一样的单张、多张、纯文字策略）
        try:
            if len(media) == 1:
                item = media[0]
                if isinstance(item, InputMediaPhoto):
                    await context.bot.send_photo(admin_id, photo=item.media, caption=combined_text)
                else:
                    await context.bot.send_video(admin_id, video=item.media, caption=combined_text)
            elif len(media) > 1:
                # 重建第一张带 caption
                if isinstance(media[0], InputMediaPhoto):
                    media[0] = InputMediaPhoto(media[0].media, caption=combined_text)
                else:
                    media[0] = InputMediaVideo(media[0].media, caption=combined_text)
                await context.bot.send_media_group(admin_id, media=media)
            elif texts:
                await context.bot.send_message(admin_id, text=combined_text)
            logger.info(f"向管理员 {admin_id} 发送内容成功")
        except Exception as e:
            logger.error(f"发送内容给管理员 {admin_id} 失败", exc_info=e)

async def collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.chat_data.get("submitting"):
        context.chat_data.setdefault("pending", []).append(update.message)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    raw = query.data or ""
    # 容错：确保 data 格式正确
    if ":" in raw:
        action, mid = raw.split(":", 1)
    else:
        # 格式不对就提前返回
        await query.edit_message_text("⚠️ 内部错误：回调数据格式不正确，无法处理。")
        logger.error(f"handle_callback: 无法解析 callback_data={raw}")
        return

    admin_id = query.from_user.id
    key = f"pending_{admin_id}_{mid}"
    pending = context.bot_data.pop(key, [])

    # 以下跟之前一样，组装 texts / media 并发布
    texts, media = [], []
    for m in pending:
        if m.text: texts.append(m.text)
        if m.caption: texts.append(m.caption)
        if m.photo: media.append(InputMediaPhoto(m.photo[-1].file_id))
        if m.video: media.append(InputMediaVideo(m.video.file_id))
    combined_text = "\n\n".join(texts) + f"\n\n#投稿 via @{config.BOT_CHANNEL_USERNAME.strip('@')}"

    if action == "approve":
        try:
            if len(media) == 1:
                item = media[0]
                if isinstance(item, InputMediaPhoto):
                    await context.bot.send_photo(config.BOT_CHANNEL_USERNAME, photo=item.media, caption=combined_text)
                else:
                    await context.bot.send_video(config.BOT_CHANNEL_USERNAME, video=item.media, caption=combined_text)
            elif len(media) > 1:
                if isinstance(media[0], InputMediaPhoto):
                    media[0] = InputMediaPhoto(media[0].media, caption=combined_text)
                else:
                    media[0] = InputMediaVideo(media[0].media, caption=combined_text)
                await context.bot.send_media_group(config.BOT_CHANNEL_USERNAME, media=media)
            else:
                await context.bot.send_message(config.BOT_CHANNEL_USERNAME, text=combined_text)

            await query.edit_message_text("✅ 已发布到频道。")
        except Exception as e:
            logger.error("发布到频道失败", exc_info=e)
            await query.edit_message_text("🚫 发布失败，请稍后再试。")
    else:
        await query.edit_message_text("🚫 投稿已拒绝。")

async def pingadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text="✅ Bot 通知成功")
        except Conflict:
            logger.warning(f"pingadmin 冲突, admin={admin_id}")
    await update.message.reply_text("✅ 测试消息已发送给所有管理员。")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    err = context.error
    if isinstance(err, Conflict):
        logger.warning("Conflict 刷新轮询冲突，继续执行。")
        return
    logger.error("未处理异常：", exc_info=err)

if __name__ == "__main__":
    logger.info(f"ADMIN_IDS={config.ADMIN_IDS}")
    req = HTTPXRequest(connect_timeout=5.0, read_timeout=20.0)
    app = Application.builder() \
        .token(config.BOT_TOKEN) \
        .build()
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(inline_button_handler, pattern="^(start_submit|finish_submit)$"))
    app.add_handler(CommandHandler("submit", submit))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("pingadmin", pingadmin))
    app.add_handler(MessageHandler(filters.ALL, collect))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot running...")
    app.run_polling(drop_pending_updates=True)
