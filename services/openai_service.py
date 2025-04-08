import re
import logging
import os
import asyncio
from openai import AsyncOpenAI

# إعدادات التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_errors.log'),
        logging.StreamHandler()
    ]
)

# استخراج مفتاح API من متغيرات البيئة
API_KEY = os.getenv('OPENROUTER_API_KEY')
if not API_KEY:
    logging.error("لم يتم العثور على OPENROUTER_API_KEY في متغيرات البيئة")

aclient = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

async def clean_content(text):
    """دالة محسنة لتنظيف المحتوى"""
    if not text:
        return ""
    
    try:
        # السماح بالأحرف العربية والترقيم الأساسي
        arabic_chars = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
        allowed_symbols = r'[#@_،؛:؟!ـ.، \n\-]'
        numbers = r'[0-9٠-٩]'
        emojis = r'[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
        
        pattern = fr'[^{arabic_chars}{allowed_symbols}{numbers}{emojis}]'
        
        cleaned = re.sub(pattern, '', str(text))
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'[ ]{2,}', ' ', cleaned)
        return cleaned.strip()
    
    except Exception as e:
        logging.error(f"خطأ في تنظيف المحتوى: {str(e)}")
        return str(text)[:500]

async def generate_post(user_input, platform, max_retries=3):
    """الإصدار النهائي المعدل بدون أخطاء"""
    platform_config = {
        "تويتر": {
            "model": "deepseek/deepseek-v3-base:free",
            "max_tokens": 280,
            "template": """
            🌟 {input}\n
            - النقطة الأولى
            - النقطة الثانية
            - النقطة الثالثة
            #هاشتاق1 #هاشتاق2
            """
        },
        "لينكدإن": {
            "model": "meta-llama/llama-3-70b-instruct:nitro",
            "max_tokens": 500,
            "template": """
            🚀 {input}\n\n
            1. العنصر الأول
            2. العنصر الثاني
            3. العنصر الثالث\n\n
            #هاشتاق1 #هاشتاق2 #هاشتاق3
            """
        }
    }

    if not API_KEY:
        return "⚠️ إعدادات النظام غير مكتملة (مفتاح API مفقود)"

    if platform not in platform_config:
        return "⚠️ المنصة غير مدعومة. الخيارات المتاحة: تويتر، لينكدإن"

    for attempt in range(max_retries):
        try:
            logging.info(f"محاولة إنشاء منشور لـ {platform} (المحاولة {attempt + 1})")
            
            response = await aclient.chat.completions.create(
                model=platform_config[platform]["model"],
                messages=[
                    {
                        "role": "system", 
                        "content": platform_config[platform]["template"].format(input=user_input)
                    },
                    {"role": "user", "content": user_input}
                ],
                temperature=0.7,
                max_tokens=platform_config[platform]["max_tokens"],
                timeout=30.0
            )

            if not response or not response.choices:
                raise ValueError("استجابة فارغة من الخادم")

            content = response.choices[0].message.content
            cleaned_content = await clean_content(content)
            
            if not cleaned_content or len(cleaned_content) < 30:
                raise ValueError("المحتوى الناتج غير كافٍ")
                
            logging.info("تم إنشاء المنشور بنجاح")
            return cleaned_content

        except Exception as e:
            logging.error(f"فشلت المحاولة {attempt + 1}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
            continue
    
    return "⚠️ تعذر إنشاء المنشور بعد عدة محاولات. يرجى:\n- التحقق من اتصال الإنترنت\n- تعديل الطلب\n- المحاولة لاحقاً"
