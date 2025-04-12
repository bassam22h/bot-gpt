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
    examples = {
        "المغربية": """\
- استعمل كلمات مثل: "واخّا"، "بزاف"، "دابا"، "خويا"، "نعيقو"، "زعما"، "خاي"، "عفاك"، "مزيان"، "حاجة زوينة"
- اكتب باللهجة المغربية بأسلوب عام يناسب المنشورات العامة.
- تجنب العبارات الدردشة الشخصية أو التحايا.
- أدرج الكلمات ضمن الجمل بشكل منطقي طبيعي بدون مبالغة.
""",
        "المصرية": """\
- استعمل كلمات زي: "يلا بينا"، "جامد أوي"، "كده يعني"، "بص يا معلم"، "حكاية"، "حلو جدًا"، "تمام التمام"، "إوعى تفوتك"، "من الآخر"، "على طول"
- اكتب باللهجة المصرية بأسلوب عام يناسب المنشورات العامة.
- تجنب صيغة الدردشة الشخصية.
- أدرج الكلمات في سياق الجمل بشكل طبيعي.
""",
        "اليمنية": """\
- استخدم كلمات مثل: "عادك"، "شوف"، "معك خبر؟"، "شوية"، "قدك"، "تمام"، "طيب"، "ابسر"، "احزر"، "خليك"، "مرتاح"، "مفتهن"، "ماشي"، "مافيش"، "شوعه"، "حالي"، "شمات"، "سابر"، "طافح"، "أيوه"، "وينك"، "فخر"، "شجاع"، "صنديد"، "قدوة"، "بطل"، "مواقف رجولية"
- اكتب باللهجة اليمنية بأسلوب عام راقٍ يناسب المنشورات العامة.
- تجنب العبارات الموجهة لشخص أو دردشة كـ: "عادك تتذكر؟" أو "أوريك"
- أدرج الكلمات في سياق الجمل بشكل منطقي دون مبالغة.
""",
        "الشامية": """\
- استعمل كلمات مثل: "هلّق"، "شو القصة"، "كتير"، "تمام"، "بالهداوة"، "منيح"، "ياريت"، "عنجد"، "بسيطة"، "عال العال"، "قديش"
- اكتب باللهجة الشامية بأسلوب عام يناسب المنشورات العامة.
- تجنب العبارات الحميمية أو الدردشة المباشرة.
- أدرج الكلمات ضمن الجمل بشكل منطقي طبيعي.
""",
        "الخليجية": """\
- استعمل كلمات مثل: "تصدق"، "زين"، "يا طويل العمر"، "وش السالفة"، "مرة"، "واجد"، "على طاري"، "حيل"، "يا بعد حيي"، "طيّب"، "معقولة"
- اكتب باللهجة الخليجية بأسلوب عام يناسب المنشورات العامة.
- تجنب صيغة السوالف أو المجالس.
- أدرج الكلمات في سياق الجمل بشكل منطقي طبيعي.
"""
    }
    return examples.get(dialect, "")

def generate_twitter_post(user_input, dialect=None):
    try:
        style_note = f"\nاكتب باللهجة {dialect} بأسلوب راقٍ يناسب منشور عام.\n{dialect_examples(dialect)}" if dialect else ""
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME,
            },
           "model="mistralai/mistral-7b-instruct:free",
            messages=[
                {"role": "system", "content": f"""
أنت كاتب محتوى عربي محترف لمنصات التواصل.
- أنشئ تغريدة جذابة حول الفكرة التالية.
- استخدم أسلوبًا بسيطًا وواضحًا وراقيًا.
- لا تكرر الصياغات الشائعة.
- لا تستخدم هاشتاقات.
- أضف إيموجي معبّرة حسب السياق.
{style_note}
""" },
                {"role": "user", "content": user_input}
            ],
            temperature=0.7,
            max_tokens=300,
            timeout=25.0
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"خطأ في إنشاء تغريدة: {str(e)}")
        return None

def generate_response(user_input, platform, dialect=None, max_retries=None):
    platform_config = {
        "تويتر": {
            "generator": generate_twitter_post,
            "emojis": ["🔥", "💡", "🚀", "✨", "🎯"],
        },
        "لينكدإن": {
            "model="mistralai/mistral-7b-instruct:free",
            "max_tokens": 600,
            "template": """
أنت كاتب محتوى محترف لمنصة لينكدإن.
أنشئ منشورًا مهنيًا واضحًا يتحدث عن: "{input}"
- اجعل الفكرة الأساسية واضحة من البداية
- أضف ثلاث نقاط أو خطوات عملية
- أنهِ المنشور برسالة ملهمة أو نصيحة
- استخدم أسلوب بسيط راقٍ
- لا تضف هاشتاقات
""",
            "emojis": ["💼", "📈", "🏆", "🔍", "🚀"],
        },
        "إنستغرام": {
            "model="mistralai/mistral-7b-instruct:free",
            "max_tokens": 450,
            "template": """
أنت صانع محتوى إنستغرام.
اكتب منشورًا ملهمًا أو تحفيزيًا عن: "{input}"
- اجعل الأسلوب مشوقًا وعاطفيًا
- استخدم جمل قصيرة
- أضف إيموجي معبرة
- لا تضف هاشتاقات
""",
            "emojis": ["❤️", "🌟", "📸", "💫", "🌈"],
        }
    }

    if not API_KEY:
        return "⚠️ يرجى التحقق من إعدادات النظام (مفتاح API مفقود)"

    if platform not in platform_config:
        return f"⚠️ المنصة غير مدعومة. الخيارات: {', '.join(platform_config.keys())}"

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
                    raise ValueError("فشل إنشاء التغريدة")
            else:
                cfg = platform_config[platform]
                style_note = f"\nاكتب باللهجة {dialect} بأسلوب عام.\n{dialect_examples(dialect)}" if dialect else ""
                system_prompt = cfg["template"].format(input=user_input) + style_note
                user_prompt = f"أنشئ منشورًا إبداعيًا. استخدم هذه الإيموجي: {', '.join(random.sample(cfg['emojis'], 3))}"

                response = client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": SITE_URL,
                        "X-Title": SITE_NAME,
                    },
                    model=cfg["model"],
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.75,
                    max_tokens=cfg["max_tokens"],
                    timeout=30.0
                )
                content = response.choices[0].message.content

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
