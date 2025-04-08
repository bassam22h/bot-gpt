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

async def generate_post(user_input, platform, max_retries=3):
    """نسخة محسنة مع التعامل مع متغيرات البيئة"""
    config = {
        "تويتر": {
            "model": "deepseek/deepseek-v3-base:free",
            "max_tokens": 300,
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
        return "⚠️ إعدادات النظام غير مكتملة. يرجى مراجعة الإدارة."

    if platform not in config:
        return "⚠️ المنصة غير مدعومة. اختر: تويتر أو لينكدإن"

    for attempt in range(max_retries):
        try:
            response = await aclient.chat.completions.create(
                model=config[platform]["model"],
                messages=[
                    {"role": "system", "content": config[platform]["template"]},
                    {"role": "user", "content": user_input}
                ],
                temperature=0.7,
                max_tokens=config[platform]["max_tokens"],
                timeout=30.0
            )

            if not response.choices:
                raise ValueError("استجابة فارغة من الخادم")

            content = response.choices[0].message.content
            return self._clean_content(content)

        except Exception as e:
            logging.error(f"المحاولة {attempt+1} فشلت: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
    
    return "⚠️ فشل إنشاء المنشور. يرجى المحاولة لاحقاً."

def _clean_content(text):
    """تنظيف المحتوى مع التحقق من الجودة"""
    # ... (نفس دالة التنظيف السابقة)
    return cleaned_text
