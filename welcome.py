import config
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from models import Session, Welcome  # 确保 models.py 在同一目录下

# —— 配置 —— 
TOKEN = config.BOT_TOKEN
ADMINS = getattr(config, 'ADMINS', [])

logging.basicConfig(level=logging.INFO)

# —— 强化的管理员检测 —— 
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    检查是否为超级用户或 Telegram 群组/频道管理员。
    优先检查 config.ADMINS 配置，其次再校验 Bot API 返回的群/频道管理员列表。
    """
    user_id = update.effective_user.id
    logging.info(f"[DEBUG] 用户ID为：{user_id} ")
    
    # 1. 配置中的超级用户
    if user_id in ADMINS:
        logging.info(f"[DEBUG] 用户 {user_id} 在 ADMINS 列表中，直接授权。")
        return True

    chat = update.effective_chat
    chat_id = chat.id

    # 2. 校验用户在群中的角色
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
        logging.info(f"[DEBUG] get_chat_member status: {member.status}")
        if member.status in ('creator', 'administrator'):
            return True
    except Exception as e:
        logging.warning(f"[WARN] get_chat_member 失败: {e}")

    # 3. 校验群管理员列表
    try:
        admins = await context.bot.get_chat_administrators(chat_id)
        admin_ids = [adm.user.id for adm in admins]
        logging.info(f"[DEBUG] 当前群管理员：{admin_ids}")
        if user_id in admin_ids:
            return True
    except Exception as e:
        logging.warning(f"[WARN] get_chat_administrators 失败: {e}")

    # 4. 如果是频道关联讨论组，可额外检查频道管理员
    linked_id = getattr(chat, 'linked_chat_id', None)
    if linked_id:
        try:
            linked_admins = await context.bot.get_chat_administrators(linked_id)
            linked_ids = [adm.user.id for adm in linked_admins]
            logging.info(f"[DEBUG] 关联频道管理员：{linked_ids}")
            if user_id in linked_ids:
                return True
        except Exception as e:
            logging.warning(f"[WARN] 获取关联频道管理员失败: {e}")

    return False

# —— 添加欢迎消息 —— 
async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"):
        return await update.effective_message.reply_text("❌ 本命令只能在群组中使用。")
    if not await is_admin(update, context):
        return await update.effective_message.reply_text("❌ 只有管理员可用此命令。")

    text = update.effective_message.text.partition(' ')[2].strip()
    if not text:
        return await update.effective_message.reply_text("用法：/set_welcome 欢迎语 {user}")

    session = Session()
    w = Welcome(chat_id=update.effective_chat.id, text=text)
    session.add(w)
    session.commit()
    await update.effective_message.reply_text(f"✅ 添加欢迎消息 (ID={w.id})。")

# —— 删除欢迎消息 —— 
async def del_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ("group", "supergroup"):
        return await update.effective_message.reply_text("❌ 本命令只能在群组中使用。")
    if not await is_admin(update, context):
        return await update.effective_message.reply_text("❌ 只有管理员可用此命令。")

    args = context.args
    if not args or not args[0].isdigit():
        return await update.effective_message.reply_text("用法：/del_welcome <欢迎消息ID>")
    wid = int(args[0])

    session = Session()
    w = session.query(Welcome).filter_by(id=wid, chat_id=update.effective_chat.id).first()
    if not w:
        return await update.effective_message.reply_text("❌ 未找到指定 ID 的欢迎消息。")

    session.delete(w)
    session.commit()
    await update.effective_message.reply_text(f"🗑️ 删除欢迎消息 ID={wid}。")

# —— 监听并欢迎新成员 —— 
async def welcome_new(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.new_chat_members:
        return

    session = Session()
    rows = session.query(Welcome).filter_by(chat_id=update.effective_chat.id).all()
    for member in update.message.new_chat_members:
        for w in rows:
            text = w.text.replace("{user}", member.mention_html())
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=text,
                parse_mode='HTML'
            )

# —— 主入口 —— 
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("set_welcome", set_welcome))
    app.add_handler(CommandHandler("del_welcome", del_welcome))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_new))
    app.run_polling()
