import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, ContextTypes
)
from config import TOKEN, ADMIN_ID  # تأكد من تعريف ADMIN_ID في متغيرات البيئة
from handlers.start import start_handler, check_subscription_callback
from handlers.generate import generate_post_handler, platform_choice, event_details, PLATFORM_CHOICE, EVENT_DETAILS

# معالج الأخطاء
def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Error occurred: {context.error}")

# إرسال رسالة لجميع المستخدمين
async def send_message_to_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat.id != ADMIN_ID:
        await update.message.reply("ليس لديك صلاحية للقيام بهذا الأمر.")
        return

    message = ' '.join(context.args)  # الحصول على الرسالة من المعاملات
    if not message:
        await update.message.reply("من فضلك، أرسل رسالة لإرسالها لجميع المستخدمين.")
        return
    
    # قراءة قائمة المستخدمين من ملف JSON أو قاعدة بيانات
    users = []  # استبدل هذا بالبيانات الفعلية للمستخدمين
    for user_id in users:
        try:
            await context.bot.send_message(user_id, message)
        except Exception as e:
            logging.error(f"Failed to send message to {user_id}: {e}")

    await update.message.reply(f"تم إرسال الرسالة إلى {len(users)} مستخدم.")

# التحقق من الإحصاءات
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # إضافة سجل للتأكد من أن المعالج تم الوصول إليه
    logging.info(f"Received /stats command from chat ID: {update.message.chat.id}")

    if update.message.chat.id != ADMIN_ID:
        await update.message.reply("ليس لديك صلاحية لعرض الإحصاءات.")
        return
    
    # افترض أن لديك وظيفة لحساب الإحصاءات مثل عدد المستخدمين
    num_users = len([])  # استبدل هذا بقيمة عدد المستخدمين الفعلي
    await update.message.reply(f"إجمالي عدد المستخدمين: {num_users}")

def main():
    logging.basicConfig(level=logging.INFO)

    # تحديد رابط الويب هوك
    webhook_url = f"https://{os.getenv('RENDER_APP_NAME')}.onrender.com/{TOKEN}"

    app = ApplicationBuilder().token(TOKEN).build()

    # إضافة معالجات الأوامر
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(check_subscription_callback, pattern="^check_subscription$"))

    # إضافة المعالجين الخاصين بالحوار
    conv = ConversationHandler(
        entry_points=[CommandHandler("generate", generate_post_handler)],
        states={
            PLATFORM_CHOICE: [MessageHandler(filters.TEXT, platform_choice)],
            EVENT_DETAILS: [MessageHandler(filters.TEXT, event_details)],
        },
        fallbacks=[]
    )
    app.add_handler(conv)

    # إضافة معالج الأخطاء
    app.add_error_handler(error_handler)

    # إضافة معالجات الأوامر الخاصة بالمشرف
    app.add_handler(CommandHandler("send_all", send_message_to_all))
    app.add_handler(CommandHandler("stats", show_stats))

    # استخدام المنفذ 8443
    if os.getenv("RENDER"):
        app.run_webhook(
            listen="0.0.0.0",  # استماع على جميع الواجهات
            port=8443,  # المنفذ 8443
            url_path=TOKEN,  # استخدام التوكن كـ URL path
            webhook_url=webhook_url  # رابط الويب هوك
        )
    else:
        app.run_polling()

if __name__ == "__main__":
    main()
