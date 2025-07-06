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
    await update.message.reply_text(config.BOT_WELCOME_TEXT)
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("开始投稿", callback_data="start_submit"),
        InlineKeyboardButton("完成投稿", callback_data="finish_submit"),
    ]])
    await update.message.reply_text(
        "请选择操作：",
        reply_markup=keyboard
    )


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

    data["submitting"] = False
    await update.message.reply_text("✅ 投稿已提交给管理员审核。",
        reply_markup=ReplyKeyboardMarkup([[]], resize_keyboard=True))

    texts, media = [], []
    for m in pending:
        if m.text: texts.append(m.text)
        if m.caption: texts.append(m.caption)
        if m.photo: media.append(InputMediaPhoto(m.photo[-1].file_id))
        if m.video: media.append(InputMediaVideo(m.video.file_id))
    combined_text = '#投稿\n' + '\n'.join(texts) + f"\n{config.channel_info.title}\n{config.channel_info.url}\n{config.channel_info.contact}"

    for admin_id in config.ADMIN_IDS:
        try:
            msg = await context.bot.send_message(chat_id=admin_id, text=f"收到投稿 @{user.username or '无名'}")
            key = f"pending_{admin_id}_{msg.message_id}"
            context.bot_data[key] = pending.copy()

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

        try:
            if len(media) == 1:
                item = media[0]
                if isinstance(item, InputMediaPhoto):
                    await context.bot.send_photo(admin_id, photo=item.media, caption=combined_text)
                else:
                    await context.bot.send_video(admin_id, video=item.media, caption=combined_text)
            elif len(media) > 1:
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
    data = query.data or ""

    if data == "start_submit":
        fake_update = TgUpdate(update_id=update.update_id, message=query.message)
        return await submit(fake_update, context)
    elif data == "finish_submit":
        fake_update = TgUpdate(update_id=update.update_id, message=query.message)
        return await done(fake_update, context)

    if ":" in data:
        action, mid = data.split(":", 1)
        admin_id = query.from_user.id
        key = f"pending_{admin_id}_{mid}"
        pending = context.bot_data.pop(key, [])

        texts, media = [], []
        for m in pending:
            if m.text: texts.append(m.text)
            if m.caption: texts.append(m.caption)
            if m.photo: media.append(InputMediaPhoto(m.photo[-1].file_id))
            if m.video: media.append(InputMediaVideo(m.video.file_id))
        combined_text = '#投稿\n' + '\n'.join(texts) + f"\n{config.channel_info.title}\n{config.channel_info.url}\n{config.channel_info.contact}"

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
    else:
        await query.edit_message_text("⚠️ 内部错误：回调数据格式不正确，无法处理。")


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
    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("submit", submit))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^开始投稿$"), submit))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^完成投稿$"), done))
    app.add_handler(CommandHandler("pingadmin", pingadmin))
    app.add_handler(MessageHandler(filters.ALL, collect))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Bot running...")
    app.run_polling(drop_pending_updates=True)
