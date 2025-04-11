from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackContext
from config import ADMIN_IDS
from utils import (
    get_all_users, get_all_logs, reset_user_counts,
    clear_all_logs, get_daily_new_users, get_platform_usage
)
import logging
from datetime import date
from telegram.constants import ParseMode

# إعداد المسجل (logger)
logger = logging.getLogger(__name__)

def escape_markdown(text):
    """هروب الأحرف الخاصة في MarkdownV2"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            "⛔ *الوصول مرفوض\!*"
            "\nليس لديك صلاحيات المشرف\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 الإحصائيات الكاملة", callback_data="view_statistics")],
        [InlineKeyboardButton("🔄 تصفير العدادات", callback_data="reset_counts_confirm")],
        [InlineKeyboardButton("🗑️ حذف جميع السجلات", callback_data="clear_logs_confirm")],
        [InlineKeyboardButton("📢 إرسال إشعار عام", callback_data="broadcast_message")]
    ])

    await update.message.reply_text(
        f"👮‍♂️ *مرحبًا بك {escape_markdown(user.first_name)} في لوحة التحكم*"
        "\nاختر الإجراء المطلوب:",
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def handle_admin_actions(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.edit_message_text("⛔ *الوصول مرفوض\!*", parse_mode=ParseMode.MARKDOWN_V2)
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
        new_users = get_daily_new_users()
        platform_stats = get_platform_usage()

        stats_text = [
            "📈 *الإحصائيات العامة:*",
            f"👥 *إجمالي المستخدمين:* {total_users}",
            f"📝 *إجمالي المنشورات:* {total_posts}",
            f"🆕 *مستخدمين جدد اليوم:* {new_users}",
            "",
            "🏆 *أكثر المنصات استخدامًا:*"
        ]

        if platform_stats:
            stats_text.extend(
                f"{i+1}\. {escape_markdown(platform)}: {count}" 
                for i, (platform, count) in enumerate(platform_stats[:5]))
        else:
            stats_text.append("لا توجد بيانات متاحة")

        await query.edit_message_text(
            "\n".join(stats_text),
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        logger.error(f"Error showing statistics: {e}")
        await query.edit_message_text("⚠ حدث خطأ أثناء جلب الإحصائيات", parse_mode=ParseMode.MARKDOWN_V2)

async def handle_reset_counts(query, action):
    if action == "reset_counts_confirm":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم، تأكيد", callback_data="reset_counts_execute")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="reset_counts_cancel")]
        ])
        await query.edit_message_text(
            "⚠ *تأكيد العملية*"
            "\nهل أنت متأكد من تصفير جميع عدادات المستخدمين\?",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    elif action == "reset_counts_execute":
        reset_user_counts()
        await query.edit_message_text("✅ تم تصفير العدادات بنجاح", parse_mode=ParseMode.MARKDOWN_V2)
    elif action == "reset_counts_cancel":
        await query.edit_message_text("❌ تم إلغاء العملية", parse_mode=ParseMode.MARKDOWN_V2)

async def handle_clear_logs(query, action):
    if action == "clear_logs_confirm":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ نعم، تأكيد", callback_data="clear_logs_execute")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="clear_logs_cancel")]
        ])
        await query.edit_message_text(
            "⚠ *تأكيد العملية*"
            "\nهل أنت متأكد من حذف جميع سجلات المنشورات\?",
            reply_markup=keyboard,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    elif action == "clear_logs_execute":
        clear_all_logs()
        await query.edit_message_text("✅ تم حذف السجلات بنجاح", parse_mode=ParseMode.MARKDOWN_V2)
    elif action == "clear_logs_cancel":
        await query.edit_message_text("❌ تم إلغاء العملية", parse_mode=ParseMode.MARKDOWN_V2)

async def start_broadcast(query, context):
    context.user_data['awaiting_broadcast'] = True
    await query.edit_message_text(
        "📢 *وضع الإرسال العام*"
        "\nأرسل الآن الرسالة التي تريد إرسالها لجميع المستخدمين:",
        parse_mode=ParseMode.MARKDOWN_V2
    )

async def receive_broadcast_message(update: Update, context: CallbackContext):
    if not context.user_data.get('awaiting_broadcast'):
        return

    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ *الوصول مرفوض\!*", parse_mode=ParseMode.MARKDOWN_V2)
        return

    message = update.message.text
    users = get_all_users().keys()

    success = 0
    failed = 0
    progress_msg = await update.message.reply_text("⏳ جاري الإرسال\.\.\.", parse_mode=ParseMode.MARKDOWN_V2)

    for uid in users:
        try:
            await context.bot.send_message(uid, message)
            success += 1
        except Exception as e:
            logger.error(f"Failed to send to {uid}: {e}")
            failed += 1

    context.user_data.pop('awaiting_broadcast', None)
    await progress_msg.edit_text(
        "✅ *تم إرسال الإشعار*"
        f"\n• تم بنجاح: {success}"
        f"\n• فشل الإرسال: {failed}",
        parse_mode=ParseMode.MARKDOWN_V2
    )
