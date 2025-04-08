import re
import logging
import os
import asyncio
from openai import AsyncOpenAI

# إعدادات التسجيل المتقدمة
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_errors.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# استخراج مفتاح API من متغيرات البيئة
API_KEY = os.getenv('OPENROUTER_API_KEY')
if not API_KEY:
    logging.error("OPENROUTER_API_KEY غير موجود في متغيرات البيئة")

aclient = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

async def clean_content(text):
    """دالة متقدمة لتنظيف المحتوى"""
    if not text:
        return ""
    
    try:
        # قائمة موسعة بالمسموحات
        arabic_chars = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
        allowed_symbols = r'[#@_،؛:؟!ـ.، \n\-*]'
        emojis = r'[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
        
        # التنظيف الأساسي
        cleaned = re.sub(fr'[^{arabic_chars}{allowed_symbols}{emojis}]', '', str(text))
        
        # تحسين التنسيق
        cleaned = re.sub(r'\*+', '•', cleaned)  # استبدال النجوم بنقاط
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'[ ]{2,}', ' ', cleaned)
        
        return cleaned.strip()
    
    except Exception as e:
        logging.error(f"خطأ في تنظيف النص: {str(e)}")
        return str(text)[:500]

async def generate_post(user_input, platform, max_retries=3):
    """الإصدار المحسن مع دعم كافة المنصات"""
    platform_config = {
        "تويتر": {
            "model": "deepseek/deepseek-v3-base:free",
            "max_tokens": 280,
            "template": """
            🌟 {input}\n\n
            • النقطة الأولى (استخدم إيموجي مناسب هنا)
            • النقطة الثانية (استخدم إيموجي مناسب هنا)
            • النقطة الثالثة (استخدم إيموجي مناسب هنا)\n\n
            {hashtags}
            """,
            "emojis": ["🚀", "💡", "✨", "🌱", "🔥"],
            "hashtags": "#تطوير #نجاح #إبداع"
        },
        "لينكدإن": {
            "model": "meta-llama/llama-3-70b-instruct:nitro",
            "max_tokens": 600,
            "template": """
            🎯 {input}\n\n
            1️⃣ النقطة الأولى: وصف مفصل هنا
            2️⃣ النقطة الثانية: وصف مفصل هنا
            3️⃣ النقطة الثالثة: وصف مفصل هنا\n\n
            {hashtags}
            """,
            "emojis": ["🚀", "💼", "📈", "👥", "🏆"],
            "hashtags": "#تطوير_المهارات #ريادة_الأعمال #النمو_المهني"
        },
        "إنستغرام": {
            "model": "anthropic/claude-3-opus",
            "max_tokens": 400,
            "template": """
            ✨ {input}\n\n
            🌸 النقطة الأولى
            🌟 النقطة الثانية
            💎 النقطة الثالثة\n\n
            {hashtags}
            """,
            "emojis": ["📸", "❤️", "✨", "🌸", "🌟"],
            "hashtags": "#إبداع #تصوير #تطوير_ذات"
        }
    }

    if not API_KEY:
        return "⚠️ يرجى التحقق من إعدادات النظام (مفتاح API مفقود)"

    if platform not in platform_config:
        return f"⚠️ المنصة غير مدعومة. الخيارات المتاحة: {', '.join(platform_config.keys())}"

    for attempt in range(max_retries):
        try:
            logging.info(f"جاري إنشاء منشور لـ {platform} - المحاولة {attempt + 1}")
            
            # إعداد المحتوى الديناميكي
            selected_emojis = platform_config[platform]["emojis"][:3]
            hashtags = platform_config[platform]["hashtags"]
            
            response = await aclient.chat.completions.create(
                model=platform_config[platform]["model"],
                messages=[
                    {
                        "role": "system",
                        "content": platform_config[platform]["template"].format(
                            input=user_input,
                            hashtags=hashtags
                        )
                    },
                    {
                        "role": "user",
                        "content": f"أنشئ منشورًا عن: {user_input}\nاستخدم هذه الإيموجيز: {', '.join(selected_emojis)}"
                    }
                ],
                temperature=0.7,
                max_tokens=platform_config[platform]["max_tokens"],
                timeout=30.0
            )

            if not response or not response.choices:
                raise ValueError("استجابة فارغة من الخادم")

            content = response.choices[0].message.content
            cleaned_content = await clean_content(content)
            
            # ضمان الجودة النهائية
            if not cleaned_content or len(cleaned_content) < 50:
                raise ValueError("المحتوى الناتج غير كافٍ")
                
            if not any(emoji in cleaned_content for emoji in selected_emojis):
                cleaned_content = f"{selected_emojis[0]} {cleaned_content}"
                
            logging.info("تم إنشاء المنشور بنجاح")
            return cleaned_content

        except Exception as e:
            logging.error(f"خطأ في المحاولة {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            continue
    
    return "⚠️ فشل إنشاء المنشور. يرجى:\n- التحقق من اتصال الإنترنت\n- تعديل النص المدخل\n- المحاولة لاحقًا"
