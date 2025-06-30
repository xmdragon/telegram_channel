import config
import warnings
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

warnings.filterwarnings("ignore", category=UserWarning)

# ———— /submit：开始投稿 —————————————————————————————————————
async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["pending"] = []
    context.chat_data["submitting"] = True
    await update.message.reply_text(
        "✅ 已进入投稿模式，请连续发送文字、图片或视频，发送完毕后请发送 /done 提交。"
    )

# ———— /done：结束投稿并预览给管理员 —————————————————————————
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_data = context.chat_data

    if not chat_data.get("submitting"):
        await update.message.reply_text("⚠️ 你还没开始投稿，请先发送 /submit 。")
        return

    pending = chat_data.get("pending", [])
    if not pending:
        await update.message.reply_text("⚠️ 你还没有发送任何内容，无法提交。")
        return

    # 关闭投稿模式
    chat_data["submitting"] = False

    # 确认给用户
    await update.message.reply_text("✅ 投稿已提交给管理员审核，请稍后…")

    # —— 调试：打印一下我们要发给谁 —— 
    print(f"[DEBUG] Sending preview to admin_id = {config.BOT_ADMIN_ID}")

    # 给管理员发预览
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ 发布", callback_data="approve"),
        InlineKeyboardButton("🚫 拒绝", callback_data="reject"),
    ]])
    first = pending[0]
    uname = first.from_user.username if first.from_user else user.username or "无名"
    await context.bot.send_message(
        chat_id=config.BOT_ADMIN_ID,
        text=f"收到一条投稿来自 @{uname}",
        reply_markup=kb,
    )

    # 收集文字和媒体
    texts = []
    media = []
    for m in pending:
        if m.text:
            texts.append(m.text)
        elif m.photo:
            media.append(InputMediaPhoto(m.photo[-1].file_id))
        elif m.video:
            media.append(InputMediaVideo(m.video.file_id))

    # 先发文字
    if texts:
        combined = "\n\n".join(texts) + f"\n\n#投稿 via @{config.BOT_CHANNEL_USERNAME.strip('@')}"
        await context.bot.send_message(chat_id=config.BOT_ADMIN_ID, text=combined)

    # 再发纯媒体轮播
    if media:
        await context.bot.send_media_group(chat_id=config.BOT_ADMIN_ID, media=media)


# ———— 收集所有消息 ———————————————————————————————————————
async def collect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.chat_data.get("submitting"):
        # 只在投稿模式下才收集
        msg = update.message
        if msg:
            context.chat_data.setdefault("pending", []).append(msg)

# ———— 管理员审核回调 ——————————————————————————————————————
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    pending = context.chat_data.get("pending", [])
    if not pending:
        await query.edit_message_text("⚠️ 投稿已超时或不存在。")
        return

    if action == "approve":
        # 同样逻辑：文字 + 轮播
        texts = []
        media = []
        for m in pending:
            if m.text:
                texts.append(m.text)
            elif m.photo:
                media.append(InputMediaPhoto(m.photo[-1].file_id))
            elif m.video:
                media.append(InputMediaVideo(m.video.file_id))

        if texts:
            combined = "\n\n".join(texts) + f"\n\n#投稿 via @{config.BOT_CHANNEL_USERNAME.strip('@')}"
            await context.bot.send_message(chat_id=config.BOT_CHANNEL_USERNAME, text=combined)

        if media:
            await context.bot.send_media_group(chat_id=config.BOT_CHANNEL_USERNAME, media=media)

        await query.edit_message_text("✅ 已发布到频道。")
    else:
        await query.edit_message_text("🚫 投稿已拒绝。")

    # 清理
    context.chat_data.pop("pending", None)
    context.chat_data.pop("submitting", None)

# ———— 启动 ——————————————————————————————————————————————
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("submit", submit))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(MessageHandler(filters.ALL, collect))
    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
