from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackContext
from config import ADMIN_IDS
from utils import (
    get_all_users, get_all_logs, reset_user_counts,
    clear_all_logs, get_daily_new_users, get_platform_usage
)
import logging

# إعداد المسجل (logger)
logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            "⛔️ <b>الوصول مرفوض!</b>\n"
            "ليس لديك صلاحيات المشرف.",
            parse_mode='HTML'
        )
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الإحصائيات الكاملة", callback_data="view_statistics")],
        [InlineKeyboardButton("🔄 تصفير العدادات", callback_data="reset_counts_confirm")],
        [InlineKeyboardButton("🗑️ حذف جميع السجلات", callback_data="clear_logs_confirm")],
        [InlineKeyboardButton("📢 إرسال إشعار عام", callback_data="broadcast_message")]
    ])

    await update.message.reply_text(
        f"👮‍♂️ <b>مرحبًا بك {user.first_name} في لوحة التحكم</b>\n"
        "اختر الإجراء المطلوب:",
        reply_markup=keyboard,
        parse_mode='HTML'
    )

async def handle_admin_actions(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔️ الوصول مرفوض!")
        return

    action = query.data

    if action == "view_statistics":
        await show_statistics(query)
    elif action.startswith("reset_counts"):
        await handle_reset_counts(query, action)
    elif action.startswith("clear_logs"):
        await handle_clear_logs(query, action)
    elif action == "broadcast_message":
        await start_broadcast(query, context)

async def show_statistics(query):
    try:
        users = get_all_users()
        logs = get_all_logs()
        
        total_users = len(users)
        total_posts = sum(len(user_logs) for user_logs in logs.values()) if logs else 0
        new_users = len([u for u in users.values() if u.get('date') == str(date.today())])
        platform_stats = get_platform_usage()

        stats_text = [
            "📈 <b>الإحصائيات العامة:</b>",
            f"👥 <b>إجمالي المستخدمين:</b> {total_users}",
            f"📝 <b>إجمالي المنشورات:</b> {total_posts}",
            f"🆕 <b>مستخدمين جدد اليوم:</b> {new_users}",
            "",
            "🏆 <b>أكثر المنصات استخدامًا:</b>"
        ]

        if platform_stats:
            stats_text.extend(
                f"{i+1}. {platform}: {count}" 
                for i, (platform, count) in enumerate(platform_stats[:5])
        else:
            stats_text.append("لا توجد بيانات متاحة")

        await query.edit_message_text(
            "\n".join(stats_text),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error showing statistics: {e}")
        await query.edit_message_text("⚠️ حدث خطأ أثناء جلب الإحصائيات")

async def handle_reset_counts(query, action):
    if action == "reset_counts_confirm":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم، تأكيد", callback_data="reset_counts_execute")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="reset_counts_cancel")]
        ])
        await query.edit_message_text(
            "⚠️ <b>تأكيد العملية</b>\n"
            "هل أنت متأكد من تصفير جميع عدادات المستخدمين؟",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    elif action == "reset_counts_execute":
        reset_user_counts()
        await query.edit_message_text("✅ تم تصفير العدادات بنجاح")
    elif action == "reset_counts_cancel":
        await query.edit_message_text("❌ تم إلغاء العملية")

async def handle_clear_logs(query, action):
    if action == "clear_logs_confirm":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم، تأكيد", callback_data="clear_logs_execute")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="clear_logs_cancel")]
        ])
        await query.edit_message_text(
            "⚠️ <b>تأكيد العملية</b>\n"
            "هل أنت متأكد من حذف جميع سجلات المنشورات؟",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
    elif action == "clear_logs_execute":
        clear_all_logs()
        await query.edit_message_text("✅ تم حذف السجلات بنجاح")
    elif action == "clear_logs_cancel":
        await query.edit_message_text("❌ تم إلغاء العملية")

async def start_broadcast(query, context):
    context.user_data['awaiting_broadcast'] = True
    await query.edit_message_text(
        "📢 <b>وضع الإرسال العام</b>\n"
        "أرسل الآن الرسالة التي تريد إرسالها لجميع المستخدمين:",
        parse_mode='HTML'
    )

async def receive_broadcast_message(update: Update, context: CallbackContext):
    if not context.user_data.get('awaiting_broadcast'):
        return

    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔️ الوصول مرفوض!")
        return

    message = update.message.text
    users = get_all_users().keys()

    success = 0
    failed = 0
    progress_msg = await update.message.reply_text("⏳ جاري الإرسال...")

    for uid in users:
        try:
            await context.bot.send_message(uid, message)
            success += 1
        except Exception as e:
            logger.error(f"Failed to send to {uid}: {e}")
            failed += 1

    context.user_data.pop('awaiting_broadcast', None)
    await progress_msg.edit_text(
        f"✅ <b>تم إرسال الإشعار</b>\n"
        f"• تم بنجاح: {success}\n"
        f"• فشل الإرسال: {failed}",
        parse_mode='HTML'
    )
