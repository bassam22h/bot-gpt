import re
import logging
import os
import asyncio
import random
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

# إعدادات OpenRouter
SITE_URL = os.getenv('SITE_URL', 'https://your-site.com')  # اضف هذا في متغيرات البيئة إذا أردت
SITE_NAME = os.getenv('SITE_NAME', 'My Bot')  # اضف هذا في متغيرات البيئة إذا أردت

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

async def generate_twitter_post(user_input):
    """دالة مخصصة لإنشاء منشورات تويتر"""
    try:
        response = await aclient.chat.completions.create(
            extra_headers={
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME,
            },
            model="meta-llama/llama-4-maverick:free",  # تم التعديل هنا
            messages=[
                {
                    "role": "system",
                    "content": """
                    أنت خبير في كتابة تغريدات عربية فعالة.
                    المطلوب:
                    - لغة عربية فصحى واضحة
                    - طول بين 180-280 حرفاً
                    - مقدمة جذابة
                    - 2-3 نقاط رئيسية
                    - خاتمة مختصرة
                    - 2-3 هاشتاقات ذات صلة
                    - 2-3 إيموجي مناسبة
                    - تجنب الرموز الغريبة
                    """
                },
                {
                    "role": "user",
                    "content": f"الموضوع: {user_input}"
                }
            ],
            temperature=0.7,
            max_tokens=300,
            timeout=25.0
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"خطأ في إنشاء تغريدة: {str(e)}")
        return None

async def generate_post(user_input, platform, max_retries=3):
    """الدالة الرئيسية المعدلة"""
    platform_config = {
        "تويتر": {
            "generator": generate_twitter_post,
            "emojis": ["🚀", "💡", "✨", "🌱", "🔥"],
            "retry_delay": 2
        },
        "لينكدإن": {
            "model": "meta-llama/llama-4-maverick:free",  # تم التعديل هنا
            "max_tokens": 600,
            "template": """
            🎯 {input}\n\n
            1️⃣ النقطة الأولى: وصف مفصل هنا
            2️⃣ النقطة الثانية: وصف مفصل هنا
            3️⃣ النقطة الثالثة: وصف مفصل هنا\n\n
            {hashtags}
            """,
            "emojis": ["🚀", "💼", "📈", "👥", "🏆"],
            "hashtags": "#تطوير_المهارات #ريادة_الأعمال #النمو_المهني",
            "retry_delay": 3
        },
        "إنستغرام": {
            "model": "meta-llama/llama-4-maverick:free",  # تم التعديل هنا
            "max_tokens": 400,
            "template": """
            ✨ {input}\n\n
            🌸 النقطة الأولى
            🌟 النقطة الثانية
            💎 النقطة الثالثة\n\n
            {hashtags}
            """,
            "emojis": ["📸", "❤️", "✨", "🌸", "🌟"],
            "hashtags": "#إبداع #تصوير #تطوير_ذات",
            "retry_delay": 3
        }
    }

    if not API_KEY:
        return "⚠️ يرجى التحقق من إعدادات النظام (مفتاح API مفقود)"

    if platform not in platform_config:
        return f"⚠️ المنصة غير مدعومة. الخيارات المتاحة: {', '.join(platform_config.keys())}"

    for attempt in range(max_retries):
        try:
            logging.info(f"جاري إنشاء منشور لـ {platform} - المحاولة {attempt + 1}")
            
            if platform == "تويتر":
                content = await generate_twitter_post(user_input)
                if not content:
                    raise ValueError("فشل إنشاء التغريدة")
            else:
                response = await aclient.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": SITE_URL,
                        "X-Title": SITE_NAME,
                    },
                    model=platform_config[platform]["model"],
                    messages=[
                        {
                            "role": "system",
                            "content": platform_config[platform]["template"].format(
                                input=user_input,
                                hashtags=platform_config[platform]["hashtags"]
                            )
                        },
                        {
                            "role": "user",
                            "content": f"أنشئ منشورًا عن: {user_input}\nاستخدم هذه الإيموجيز: {', '.join(platform_config[platform]['emojis'][:3])}"
                        }
                    ],
                    temperature=0.7,
                    max_tokens=platform_config[platform]["max_tokens"],
                    timeout=30.0
                )
                content = response.choices[0].message.content

            cleaned_content = await clean_content(content)
            
            # ضمان الجودة النهائية
            if not cleaned_content or len(cleaned_content) < 50:
                raise ValueError("المحتوى الناتج غير كافٍ")
                
            # إضافة إيموجي إذا لم يكن موجوداً
            selected_emojis = platform_config[platform]["emojis"]
            if not any(emoji in cleaned_content for emoji in selected_emojis):
                cleaned_content = f"{random.choice(selected_emojis)} {cleaned_content}"
                
            logging.info("تم إنشاء المنشور بنجاح")
            return cleaned_content

        except Exception as e:
            logging.error(f"خطأ في المحاولة {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(platform_config[platform]["retry_delay"])
            continue
    
    return "⚠️ فشل إنشاء المنشور. يرجى:\n- التحقق من اتصال الإنترنت\n- تعديل النص المدخل\n- المحاولة لاحقًا"
