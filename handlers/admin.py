from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import ADMIN_IDS
from utils import (
    get_all_users, get_all_logs, reset_user_counts,
    clear_all_logs, get_daily_new_users, get_platform_usage
)

# التحقق من المشرف
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى لوحة التحكم.")
        return

    users = get_all_users()
    logs = get_all_logs()
    total_users = len(users)
    total_posts = sum(len(user_logs) for user_logs in logs.values()) if logs else 0
    new_users = get_daily_new_users()
    platform_ranking = get_platform_usage()  # تم التعديل هنا

    # التأكد من أن البيانات تُعاد بتنسيق مناسب (قائمة تحتوي على tuples)
    if isinstance(platform_ranking, list):
        ranking_text = "\n".join(
            [f"{idx+1}. {platform}: {count}" for idx, (platform, count) in enumerate(platform_ranking)]
        ) or "لا توجد بيانات"
    else:
        ranking_text = "لا توجد بيانات"

    text = (
        f"📊 إحصائيات البوت:\n"
        f"- المستخدمون الكلي: {total_users}\n"
        f"- منشورات اليوم: {total_posts}\n"
        f"- مستخدمون جدد اليوم: {new_users}\n\n"
        f"🏆 ترتيب المنصات:\n{ranking_text}"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("♻️ تصفير العدادات", callback_data="reset_counts")],
        [InlineKeyboardButton("🗑️ حذف جميع المنشورات", callback_data="clear_logs")],
        [InlineKeyboardButton("📢 إرسال رسالة جماعية", callback_data="broadcast")]
    ])

    await update.message.reply_text(text, reply_markup=keyboard)

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("❌ ليس لديك صلاحية.")
        return

    if query.data == "reset_counts":
        reset_user_counts()
        await query.edit_message_text("✅ تم تصفير العدادات لجميع المستخدمين.")
    elif query.data == "clear_logs":
        clear_all_logs()
        await query.edit_message_text("✅ تم حذف جميع المنشورات.")
    elif query.data == "broadcast":
        context.user_data["broadcast_mode"] = True
        await query.message.reply_text("✉️ أرسل الرسالة التي تريد إرسالها لجميع المستخدمين.")
        await query.answer()

async def receive_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("broadcast_mode"):
        return

    message = update.message.text
    users = get_all_users()

    sent = 0
    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            sent += 1
        except:
            continue

    await update.message.reply_text(f"✅ تم إرسال الرسالة إلى {sent} مستخدم.")
    context.user_data["broadcast_mode"] = False
