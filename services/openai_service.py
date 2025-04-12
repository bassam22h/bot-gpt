import re
import logging
import os
import random
from openrouter import OpenRouter

# إعدادات التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_errors.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

API_KEY = os.getenv('OPENROUTER_API_KEY')
if not API_KEY:
    logging.error("OPENROUTER_API_KEY غير موجود في متغيرات البيئة")

SITE_URL = os.getenv('SITE_URL', 'https://your-site.com')
SITE_NAME = os.getenv('SITE_NAME', 'My Bot')

client = OpenRouter(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

def clean_content(text):
    if not text:
        return ""
    try:
        arabic_chars = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
        allowed_symbols = r'[!؟.,،؛:\n\-#@_ ]'
        emojis = r'[\U0001F300-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
        cleaned = re.sub(fr'[^\n{arabic_chars}{allowed_symbols}{emojis}]', '', str(text))
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'[ ]{2,}', ' ', cleaned)
        return cleaned.strip()
    except Exception as e:
        logging.error(f"خطأ في تنظيف النص: {str(e)}")
        return str(text)[:500]

def generate_twitter_post(user_input, dialect=None):
    try:
        dialect_note = f"\nاكتب باللهجة {dialect} بشكل واضح ومباشر دون مبالغة أو كلمات جلسات، وبأسلوب عام مبسط." if dialect else ""

        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME,
            },
            model="google/gemini-2.0-flash-thinking-exp:free",
            messages=[
                {
                    "role": "system",
                    "content": f"""
أنت كاتب محتوى محترف.
مهمتك كتابة منشور جذاب وعام حول الفكرة المطلوبة.
- اجعل الأسلوب بسيطًا ومباشرًا وواضحًا.
- اكتب باللهجة المطلوبة دون مبالغة.
- لا تستخدم أسلوب جلسات مقيل.
- أضف إيموجي مناسبة ضمن النص.
- لا تستخدم هاشتاقات.
{dialect_note}
                    """
                },
                {
                    "role": "user",
                    "content": user_input
                }
            ],
            temperature=0.7,
            max_tokens=350,
            timeout=25.0
        )

        return response.choices[0].message.content

    except Exception as e:
        logging.error(f"خطأ في إنشاء المنشور: {str(e)}")
        return None

def generate_response(user_input, platform, dialect=None, max_retries=None):
    platform_config = {
        "تويتر": {
            "generator": generate_twitter_post,
            "emojis": ["🔥", "💡", "🚀", "✨", "🎯"],
        }
    }

    if not API_KEY:
        return "⚠️ يرجى التحقق من إعدادات النظام (مفتاح API مفقود)"

    if platform not in platform_config:
        return f"⚠️ المنصة غير مدعومة. الخيارات المتاحة: {', '.join(platform_config.keys())}"

    try:
        max_retries = int(max_retries)
    except (TypeError, ValueError):
        max_retries = 3

    for attempt in range(max_retries):
        try:
            logging.info(f"جاري إنشاء منشور لـ {platform} - المحاولة {attempt + 1}")

            if platform == "تويتر":
                content = platform_config[platform]["generator"](user_input, dialect)
                if not content:
                    raise ValueError("فشل إنشاء المنشور")
            else:
                raise ValueError("منصة غير مدعومة")

            cleaned = clean_content(content)
            if not cleaned or len(cleaned) < 50:
                raise ValueError("النص الناتج غير كافٍ")

            if not any(emoji in cleaned for emoji in platform_config[platform]["emojis"]):
                cleaned = f"{random.choice(platform_config[platform]['emojis'])} {cleaned}"

            logging.info("تم إنشاء المنشور بنجاح")
            return cleaned

        except Exception as e:
            logging.error(f"خطأ في المحاولة {attempt + 1}: {str(e)}")
            continue

    return "⚠️ فشل إنشاء المنشور. يرجى:\n- التأكد من الاتصال\n- المحاولة لاحقًا"
