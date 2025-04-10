from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils import (
    get_all_users, get_all_logs, reset_user_counts, clear_all_logs,
    get_daily_new_users, get_platform_usage
)

ADMIN_IDS = [123456789]  # ضع معرفك هنا كمشرف

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ ليس لديك صلاحية الوصول إلى هذه اللوحة.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 عرض الإحصائيات", callback_data="stats")],
        [InlineKeyboardButton("♻️ تصفير العدادات", callback_data="reset_counts")],
        [InlineKeyboardButton("🗑️ حذف جميع السجلات", callback_data="clear_logs")],
        [InlineKeyboardButton("📢 إرسال رسالة جماعية", callback_data="broadcast")]
    ])

    await update.message.reply_text("🔧 لوحة تحكم المشرف:", reply_markup=keyboard)

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("❌ ليس لديك صلاحية الوصول.")
        return

    if query.data == "stats":
        users = get_all_users()
        logs = get_all_logs()
        platforms = get_platform_usage()
        new_users = get_daily_new_users()

        text = f"""📊 <b>إحصائيات البوت:</b>

👥 عدد المستخدمين: <b>{len(users)}</b>
📝 عدد المنشورات: <b>{sum(len(l) for l in logs.values())}</b>

🏆 <b>أكثر المنصات استخدامًا:</b>
""" + "\n".join([f"• {p}: {c}" for p, c in platforms.items()]) + """

📈 <b>عدد المستخدمين الجدد يوميًا:</b>
""" + "\n".join([f"• {d}: {c}" for d, c in new_users.items()])

        await query.edit_message_text(text, parse_mode="HTML")

    elif query.data == "reset_counts":
        reset_user_counts()
        await query.edit_message_text("✅ تم تصفير عدد الطلبات لكل المستخدمين.")

    elif query.data == "clear_logs":
        clear_all_logs()
        await query.edit_message_text("✅ تم حذف جميع السجلات.")

    elif query.data == "broadcast":
        context.user_data["broadcast_mode"] = True
        await query.edit_message_text("✍️ أرسل الآن الرسالة التي تريد إرسالها لجميع المستخدمين:")

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("broadcast_mode"):
        message = update.message.text
        users = get_all_users()
        count = 0
        for user_id in users.keys():
            try:
                await context.bot.send_message(chat_id=user_id, text=message)
                count += 1
            except:
                pass
        context.user_data["broadcast_mode"] = False
        await update.message.reply_text(f"✅ تم إرسال الرسالة إلى {count} مستخدم.")
