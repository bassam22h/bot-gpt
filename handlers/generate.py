import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from services.openai_service import generate_response
from utils import (
    increment_user_count, require_subscription,
    get_user_data, log_post, has_reached_limit
)

PLATFORM_CHOICE, DIALECT_CHOICE, EVENT_DETAILS = range(3)

SUPPORTED_PLATFORMS = ["تويتر", "لينكدإن", "إنستغرام"]
SUPPORTED_DIALECTS = [
    "الفصحى المبسطة", "اليمنية", "الخليجية",
    "المصرية", "الشامية", "المغربية"
]
DAILY_LIMIT = 5

ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip().isdigit()]

@require_subscription
async def generate_post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS

    if not is_admin:
        if has_reached_limit(user_id, DAILY_LIMIT):
            await update.message.reply_text("⚠️ لقد وصلت للحد الأقصى من الطلبات اليوم.")
            return ConversationHandler.END

        data = get_user_data(user_id)
        count = data.get("count", 0)
        remaining = max(0, DAILY_LIMIT - count)

        await update.message.reply_text(
            f"📱 اختر المنصة:\n\nلديك {remaining} من {DAILY_LIMIT} طلبات متبقية اليوم.",
            reply_markup=ReplyKeyboardMarkup([SUPPORTED_PLATFORMS], one_time_keyboard=True, resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            "📱 اختر المنصة (لا يوجد حد للمشرفين):",
            reply_markup=ReplyKeyboardMarkup([SUPPORTED_PLATFORMS], one_time_keyboard=True, resize_keyboard=True)
        )

    return PLATFORM_CHOICE

@require_subscription
async def platform_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    platform = update.message.text

    if platform not in SUPPORTED_PLATFORMS:
        await update.message.reply_text("⚠️ المنصة غير مدعومة. اختر من القائمة.")
        return PLATFORM_CHOICE

    context.user_data["platform"] = platform
    await update.message.reply_text(
        "🗣️ اختر اللهجة التي تريد استخدامهـا:",
        reply_markup=ReplyKeyboardMarkup(
            [SUPPORTED_DIALECTS[i:i+2] for i in range(0, len(SUPPORTED_DIALECTS), 2)],
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )
    return DIALECT_CHOICE

@require_subscription
async def dialect_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dialect = update.message.text

    if dialect not in SUPPORTED_DIALECTS:
        await update.message.reply_text("⚠️ اختر اللهجة من الأزرار الظاهرة.")
        return DIALECT_CHOICE

    context.user_data["dialect"] = dialect
    await update.message.reply_text("✍️ أرسل الآن فكرة المنشور أو نصه:")
    return EVENT_DETAILS

@require_subscription
async def event_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_admin = user_id in ADMIN_IDS
    platform = context.user_data.get("platform")
    dialect = context.user_data.get("dialect")
    user_input = update.message.text

    if not is_admin:
        if has_reached_limit(user_id, DAILY_LIMIT):
            await update.message.reply_text("⚠️ لقد وصلت للحد الأقصى من الطلبات اليوم.")
            return ConversationHandler.END
        increment_user_count(user_id)
        data = get_user_data(user_id)
        remaining = max(0, DAILY_LIMIT - data.get("count", 0))
    else:
        remaining = "غير محدود"

    msg = await update.message.reply_text("⏳ يتم إنشاء المنشور...")

    try:
        result = generate_response(user_input, platform, dialect)
        log_post(user_id, platform, result)

        await context.bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
        await update.message.reply_text(result)

        if not is_admin:
            if remaining == 0:
                await update.message.reply_text("⚠️ لقد استنفدت جميع طلباتك لليوم.")
            else:
                await update.message.reply_text(f"✅ تبقى لديك {remaining} من {DAILY_LIMIT} لهذا اليوم.")
    except Exception as e:
        await context.bot.delete_message(chat_id=msg.chat.id, message_id=msg.message_id)
        await update.message.reply_text("⚠️ حدث خطأ أثناء إنشاء المنشور. حاول مجددًا.")
        raise e

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم إلغاء العملية.")
    return ConversationHandler.END
