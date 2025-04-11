from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackContext
from config import CHANNEL_USERNAME, CHANNEL_LINK
from utils import get_user_data, save_user_data
from datetime import datetime, date
import logging
from telegram.constants import ParseMode

# إعداد المسجل (logger)
logger = logging.getLogger(__name__)

clean_channel_username = CHANNEL_USERNAME.replace("@", "")

async def check_subscription(update: Update, context: CallbackContext) -> bool:
    user = update.effective_user
    try:
        member = await context.bot.get_chat_member(
            chat_id=f"@{clean_channel_username}", 
            user_id=user.id
        )
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Subscription check failed for {user.id}: {e}")
        return False

async def send_subscription_prompt(update: Update, context: CallbackContext):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 انضم للقناة", url=CHANNEL_LINK),
            InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_subscription")
        ]
    ])
    
    welcome_msg = (
        "👋 *مرحبًا بك في بوت المنشورات الذكية\!*\n\n"
        f"🔒 للوصول الكامل للميزات، يرجى الاشتراك في قناتنا:\n"
        f"https://t\.me/{clean_channel_username}\n\n"
        "بعد الاشتراك، اضغط على زر *تحقق من الاشتراك*"
    )
    
    await update.message.reply_text(
        welcome_msg,
        reply_markup=keyboard,
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True
    )

async def check_subscription_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    try:
        if await check_subscription(update, context):
            success_msg = (
                "🎉 *تم التحقق بنجاح\!*\n\n"
                "يمكنك الآن استخدام جميع ميزات البوت:\n"
                "📝 /generate \- لإنشاء منشور جديد\n"
                "👨‍💻 /admin \- لوحة التحكم للمشرفين"
            )
            await query.edit_message_text(
                success_msg,
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            await query.edit_message_text(
                "❌ *لم يتم التحقق من اشتراكك*\n\n"
                "1\. تأكد من الانضمام للقناة\n"
                "2\. اضغط على زر التحقق مرة أخرى\n"
                "3\. إذا استمرت المشكلة، حاول /start",
                parse_mode=ParseMode.MARKDOWN_V2
            )
    except Exception as e:
        logger.error(f"Subscription callback failed: {e}")
        await query.edit_message_text(
            "⚠️ حدث خطأ أثناء التحقق\. الرجاء المحاولة لاحقًا\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

async def start_handler(update: Update, context: CallbackContext):
    user = update.effective_user

    # تسجيل أو تحديث بيانات المستخدم
    try:
        existing_data = get_user_data(user.id)

        updated_data = {
            "first_name": user.first_name or "",
            "username": user.username or "",
            "date": existing_data.get("date") or str(date.today()),
            "count": existing_data.get("count", 0),
            "last_active": str(datetime.utcnow())
        }

        save_user_data(user.id, updated_data)

    except Exception as e:
        logger.error(f"Failed to register/update user {user.id}: {e}")

    # التحقق من الاشتراك
    try:
        if not await check_subscription(update, context):
            await send_subscription_prompt(update, context)
            return

        welcome_msg = (
            f"👋 *أهلاً بعودتك، {escape_markdown(user.first_name)}\!*\n\n"
            "🎯 *اختر أحد الخيارات:*\n"
            "📝 /generate \- إنشاء منشور جديد\n"
            "ℹ️ /help \- عرض التعليمات\n"
            "👨‍💻 /admin \- لوحة التحكم للمشرفين\n\n"
            "🛠️ البوت يدعم إنشاء منشورات لتويتر، لينكدإن وإنستغرام"
        )
        
        await update.message.reply_text(
            welcome_msg,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 قناتنا", url=CHANNEL_LINK)]
            ]),
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Start handler failed for {user.id}: {e}")
        await update.message.reply_text(
            "⚠️ حدث خطأ أثناء تحميل البيانات\. الرجاء المحاولة لاحقًا\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )

def escape_markdown(text):
    """هروب الأحرف الخاصة في MarkdownV2"""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)
