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

def get_dialect_style_note(dialect):
    if dialect == "المغربية":
        return "اكتب باللهجة المغربية. استعمل كلمات مثل: بزّاف، دابا، واخّا، واش، وصياغات من الحياة اليومية."
    elif dialect == "المصرية":
        return "اكتب باللهجة المصرية. استعمل كلمات مثل: جامد، أوي، كده، بص، وخلي الأسلوب مصري شعبي."
    elif dialect == "اليمنية":
        return "اكتب باللهجة اليمنية. استعمل كلمات مثل: قد، مشّت، شلّ، ذلحين، وخلي الأسلوب يمني شعبي."
    elif dialect:
        return f"استخدم أسلوب {dialect} في الكتابة."
    else:
        return ""

def generate_twitter_post(user_input, dialect=None):
    try:
        style_note = get_dialect_style_note(dialect)
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME,
            },
            model="meta-llama/llama-4-maverick:free",
            messages=[
                {"role": "system", "content": f"""
أنت خبير محتوى عربي على تويتر.
- أنشئ تغريدة جذابة حول الفكرة التالية.
- استخدم أسلوبًا بسيطًا غير رسمي.
- لا تكرر الصياغات الشائعة.
- أضف 2-3 هاشتاقات مناسبة.
- استخدم إيموجي معبّرة.
- لا تذكر "في هذه التغريدة" أو "إليك".
{style_note}
"""},
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
            "model": "meta-llama/llama-4-maverick:free",
            "max_tokens": 600,
            "template": """
أنت كاتب محتوى محترف لمنصة لينكدإن.
أنشئ منشورًا جذابًا ومهنيًا يتحدث عن: "{input}"
- اجعل الفكرة الأساسية واضحة من البداية
- أضف ثلاث نقاط أو خطوات عملية
- أنهِ المنشور برسالة ملهمة أو نصيحة واقعية
- استخدم أسلوبًا بسيطًا لكنه راقٍ
- أضف بعض الإيموجي المناسبة و3 هاشتاقات مثل: {hashtags}
{style_note}
""",
            "emojis": ["💼", "📈", "🏆", "🔍", "🚀"],
            "hashtags": "#تطوير_مهني #ريادة_أعمال #نصائح_وظيفية"
        },
        "إنستغرام": {
            "model": "meta-llama/llama-4-maverick:free",
            "max_tokens": 450,
            "template": """
أنت صانع محتوى إنستغرام.
اكتب منشورًا مميزًا بأسلوب تحفيزي أو عاطفي حول: "{input}"
- اجعل الأسلوب مشوقًا وعاطفيًا
- استخدم جمل قصيرة أو تنسيقات نقطية
- أضف إيموجي جذابة بكثرة
- ضع في النهاية 3-4 هاشتاقات مثل: {hashtags}
{style_note}
""",
            "emojis": ["❤️", "🌟", "📸", "💫", "🌈"],
            "hashtags": "#الهام #ابداع #تطوير_الذات #حب_الحياة"
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
                    raise ValueError("فشل إنشاء التغريدة")
            else:
                cfg = platform_config[platform]
                style_note = get_dialect_style_note(dialect)
                system_prompt = cfg["template"].format(
                    input=user_input,
                    hashtags=cfg["hashtags"],
                    style_note=style_note
                )

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
