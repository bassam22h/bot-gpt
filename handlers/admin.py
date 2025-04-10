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

    # إنشاء زر الإحصائيات فقط لعرض الإحصائيات عند الضغط عليه
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 عرض الإحصائيات", callback_data="view_statistics")],
        [InlineKeyboardButton("♻️ تصفير العدادات", callback_data="reset_counts")],
        [InlineKeyboardButton("🗑️ حذف جميع المنشورات", callback_data="clear_logs")],
        [InlineKeyboardButton("📢 إرسال رسالة جماعية", callback_data="broadcast")]
    ])

    await update.message.reply_text("مرحبًا بك في لوحة تحكم المشرف! اختر الإجراء الذي تود القيام به:", reply_markup=keyboard)

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("❌ ليس لديك صلاحية.")
        return

    if query.data == "view_statistics":
        # عرض الإحصائيات بعد الضغط على الزر
        users = get_all_users()
        logs = get_all_logs()
        total_users = len(users)
        total_posts = sum(len(user_logs) for user_logs in logs.values()) if logs else 0
        new_users = get_daily_new_users()
        platform_ranking = get_platform_usage()

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

        # عرض الإحصائيات للمشرف
        await query.edit_message_text(text)

    elif query.data == "reset_counts":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم, تصفير العدادات", callback_data="confirm_reset_counts")],
            [InlineKeyboardButton("❌ لا, إلغاء", callback_data="cancel_reset_counts")]
        ])
        await query.edit_message_text("⚠️ هل أنت متأكد من أنك تريد تصفير العدادات لجميع المستخدمين؟", reply_markup=keyboard)
    elif query.data == "clear_logs":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم, حذف جميع المنشورات", callback_data="confirm_clear_logs")],
            [InlineKeyboardButton("❌ لا, إلغاء", callback_data="cancel_clear_logs")]
        ])
        await query.edit_message_text("⚠️ هل أنت متأكد من أنك تريد حذف جميع المنشورات؟", reply_markup=keyboard)
    elif query.data == "broadcast":
        context.user_data["broadcast_mode"] = True
        await query.message.reply_text("✉️ أرسل الرسالة التي تريد إرسالها لجميع المستخدمين.")
        await query.answer()

# تأكيد التصرفات
async def confirm_reset_counts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_user_counts()
    await update.callback_query.edit_message_text("✅ تم تصفير العدادات لجميع المستخدمين.")

async def cancel_reset_counts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("❌ تم إلغاء عملية تصفير العدادات.")

async def confirm_clear_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_all_logs()
    await update.callback_query.edit_message_text("✅ تم حذف جميع المنشورات.")

async def cancel_clear_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text("❌ تم إلغاء عملية حذف المنشورات.")
