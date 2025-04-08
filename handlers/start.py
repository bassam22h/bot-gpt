from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from config import CHANNEL_USERNAME, CHANNEL_LINK
from .generate import generate_post_handler

async def check_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user.id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

async def send_subscription_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 اشترك في القناة", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ تم الاشتراك", callback_data="check_subscription")]
    ])
    await update.message.reply_text(
        f"🔒 للوصول إلى جميع ميزات البوت، اشترك في قناتنا: {CHANNEL_USERNAME}\n"
        "ثم اضغط 'تم الاشتراك' للتأكيد",
        reply_markup=keyboard
    )

async def check_subscription_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if await check_subscription(update, context):
        await query.edit_message_text("✅ تم التحقق من اشتراكك! يمكنك البدء الآن باستخدام /generate")
    else:
        await query.edit_message_text("❌ لم نتمكن من التحقق. تأكد من الاشتراك في القناة ثم أعد المحاولة.")

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_subscription(update, context):
        await send_subscription_prompt(update, context)
        return
    await update.message.reply_text(
        "🎉 مرحباً بك في بوت المنشورات الذكية!\n"
        "استخدم /generate لإنشاء منشور احترافي لمنصات التواصل الاجتماعي."
    )
