import re
import logging
import os
import random
from openai import OpenAI

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

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

def clean_content(text):
    """تنظيف المحتوى الناتج وإزالة الأحرف غير المرغوب فيها"""
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

def dialect_examples(dialect):
    """أمثلة للهجات المختلفة لتحسين النتائج"""
    examples = {
        "المغربية": """\
- استعمل كلمات مثل: "واخّا"، "بزاف"، "دابا"، "خويا"، "نعيقو"، "زعما"، "خاي"، "عفاك"، "مزيان"، "حاجة زوينة"
- اكتب باللهجة المغربية بأسلوب عام يناسب المنشورات العامة.
""",
        "المصرية": """\
- استعمل كلمات زي: "يلا بينا"، "جامد أوي"، "كده يعني"، "بص يا معلم"، "حكاية"، "حلو جدًا"
- اكتب باللهجة المصرية بأسلوب عام يناسب المنشورات العامة.
""",
        "اليمنية": """\
- استخدم كلمات مثل: "عادك"، "شوف"، "معك خبر؟"، "شوية"، "قدك"، "تمام"، "طيب"، "ابسر"
- اكتب باللهجة اليمنية بأسلوب عام راقٍ يناسب المنشورات العامة.
""",
        "الشامية": """\
- استعمل كلمات مثل: "هلّق"، "شو القصة"، "كتير"، "تمام"، "بالهداوة"، "منيح"، "ياريت"
- اكتب باللهجة الشامية بأسلوب عام يناسب المنشورات العامة.
""",
        "الخليجية": """\
- استعمل كلمات مثل: "تصدق"، "زين"، "يا طويل العمر"، "وش السالفة"، "مرة"، "واجد"، "على طاري"
- اكتب باللهجة الخليجية بأسلوب عام يناسب المنشورات العامة.
"""
    }
    return examples.get(dialect, "")

def generate_content(prompt, system_message, dialect=None, max_tokens=300, temperature=0.7):
    """دالة أساسية لإنشاء المحتوى باستخدام نموذج Gemini"""
    try:
        style_note = f"\nاكتب باللهجة {dialect} بأسلوب عام.\n{dialect_examples(dialect)}" if dialect else ""
        
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME,
            },
            extra_body={},  # تمت إضافته للتوافق الكامل مع API
            model="google/gemini-2.0-flash-thinking-exp:free",  # النسخة المجانية
            messages=[
                {
                    "role": "system", 
                    "content": system_message + style_note
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=30.0
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"خطأ في إنشاء المحتوى: {str(e)}")
        return None

def generate_twitter_post(user_input, dialect=None):
    """إنشاء منشور تويتر"""
    system_message = """\
أنت كاتب محتوى عربي محترف لمنصات التواصل.
- أنشئ تغريدة جذابة حول الفكرة التالية.
- استخدم أسلوبًا بسيطًا وواضحًا وراقيًا.
- لا تكرر الصياغات الشائعة.
- لا تستخدم هاشتاقات.
- أضف إيموجي معبّرة حسب السياق.
"""
    content = generate_content(user_input, system_message, dialect)
    return clean_content(content) if content else None

def generate_linkedin_post(user_input, dialect=None):
    """إنشاء منشور لينكدإن"""
    system_message = """\
أنت كاتب محتوى محترف لمنصة لينكدإن.
- أنشئ منشورًا مهنيًا واضحًا.
- اجعل الفكرة الأساسية واضحة من البداية.
- أضف ثلاث نقاط أو خطوات عملية.
- أنهِ المنشور برسالة ملهمة أو نصيحة.
- استخدم أسلوب بسيط راقٍ.
- لا تضف هاشتاقات.
"""
    content = generate_content(
        user_input, 
        system_message, 
        dialect,
        max_tokens=600,
        temperature=0.75
    )
    return clean_content(content) if content else None

def generate_instagram_post(user_input, dialect=None):
    """إنشاء منشور إنستغرام"""
    system_message = """\
أنت صانع محتوى إنستغرام.
- اكتب منشورًا ملهمًا أو تحفيزيًا.
- اجعل الأسلوب مشوقًا وعاطفيًا.
- استخدم جمل قصيرة.
- أضف إيموجي معبرة.
- لا تضف هاشتاقات.
"""
    content = generate_content(
        user_input, 
        system_message, 
        dialect,
        max_tokens=450,
        temperature=0.8
    )
    return clean_content(content) if content else None

def generate_response(user_input, platform, dialect=None, max_retries=3):
    """الدالة الرئيسية لإنشاء المحتوى حسب المنصة"""
    platform_handlers = {
        "تويتر": generate_twitter_post,
        "لينكدإن": generate_linkedin_post,
        "إنستغرام": generate_instagram_post
    }

    if not API_KEY:
        return "⚠️ يرجى التحقق من إعدادات النظام (مفتاح API مفقود)"

    if platform not in platform_handlers:
        return f"⚠️ المنصة غير مدعومة. الخيارات: {', '.join(platform_handlers.keys())}"

    for attempt in range(max_retries):
        try:
            logging.info(f"جاري إنشاء منشور لـ {platform} - المحاولة {attempt + 1}")
            
            handler = platform_handlers[platform]
            content = handler(user_input, dialect)
            
            if not content or len(content) < 50:
                raise ValueError("النص الناتج غير كافٍ")
            
            logging.info("تم إنشاء المنشور بنجاح")
            return content

        except Exception as e:
            logging.error(f"خطأ في المحاولة {attempt + 1}: {str(e)}")
            continue

    return "⚠️ فشل إنشاء المنشور. يرجى:\n- التأكد من الاتصال\n- المحاولة لاحقًا"
