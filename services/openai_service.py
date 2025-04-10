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

# إعدادات API
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
        allowed_symbols = r'[#@_،؛:؟!ـ.، \n\-*]'
        emojis = r'[\U0001F300-\U0001F5FF\U0001F600-\U0001F64F\U0001F680-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
        
        cleaned = re.sub(fr'[^{arabic_chars}{allowed_symbols}{emojis}]', '', str(text))
        cleaned = re.sub(r'\*+', '•', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        cleaned = re.sub(r'[ ]{2,}', ' ', cleaned)
        
        return cleaned.strip()
    except Exception as e:
        logging.error(f"خطأ في تنظيف النص: {str(e)}")
        return str(text)[:500]

def generate_twitter_post(user_input):
    try:
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": SITE_URL,
                "X-Title": SITE_NAME,
            },
            model="meta-llama/llama-4-maverick:free",
            messages=[
                {"role": "system", "content": """
                    أنت كاتب محترف على تويتر.
                    أنشئ تغريدة قصيرة وجذابة باللغة العربية الفصحى.
                    - ابدأ بجملة افتتاحية ملفتة
                    - قدم فكرة واحدة رئيسية
                    - استخدم هاشتاقات مرتبطة بالموضوع (2-3)
                    - أضف إيموجي إن أمكن
                    - لا تستخدم ترقيم أو تعليمات
                    - لا تكتب تنبيهات أو مقدمات مثل (إليك - هذه تغريدة - إلخ)
                """},
                {"role": "user", "content": f"{user_input}"}
            ],
            temperature=0.7,
            max_tokens=300,
            timeout=25.0
        )
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"خطأ في إنشاء تغريدة: {str(e)}")
        return None

def generate_response(user_input, platform, max_retries=3):
    platform_config = {
        "تويتر": {
            "generator": generate_twitter_post,
            "emojis": ["🚀", "💡", "✨", "🌱", "🔥"],
            "retry_delay": 2
        },
        "لينكدإن": {
            "model": "meta-llama/llama-4-maverick:free",
            "max_tokens": 600,
            "template": """
أنت خبير في إنشاء منشورات مهنية باللغة العربية على لينكدإن.
أنشئ منشورًا يسلّط الضوء على "{input}" بطريقة احترافية، تشمل:
- فكرة أساسية واضحة
- ثلاث نقاط داعمة أو خطوات تطبيقية
- لمسة تحفيزية في الختام
- استخدام هاشتاقات مثل: {hashtags}
- إدراج بعض الإيموجي المناسبة
""",
            "emojis": ["🚀", "💼", "📈", "👥", "🏆"],
            "hashtags": "#تطوير_المهارات #ريادة_الأعمال #النمو_المهني",
            "retry_delay": 3
        },
        "إنستغرام": {
            "model": "meta-llama/llama-4-maverick:free",
            "max_tokens": 400,
            "template": """
أنت صانع محتوى بصري لإنستغرام.
أنشئ منشورًا مميزًا حول "{input}":
- بأسلوب ملهم أو تحفيزي
- يحتوي على فقرات قصيرة أو نقاط جذابة
- يشمل رموز تعبيرية جميلة
- وينتهي بهاشتاقات مثل: {hashtags}
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
                content = platform_config[platform]["generator"](user_input)
                if not content:
                    raise ValueError("فشل إنشاء التغريدة")
            else:
                response = client.chat.completions.create(
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

            cleaned_content = clean_content(content)
            if not cleaned_content or len(cleaned_content) < 50:
                raise ValueError("المحتوى الناتج غير كافٍ")

            selected_emojis = platform_config[platform]["emojis"]
            if not any(emoji in cleaned_content for emoji in selected_emojis):
                cleaned_content = f"{random.choice(selected_emojis)} {cleaned_content}"

            logging.info("تم إنشاء المنشور بنجاح")
            return cleaned_content

        except Exception as e:
            logging.error(f"خطأ في المحاولة {attempt + 1}: {str(e)}")
            continue

    return "⚠️ فشل إنشاء المنشور. يرجى:\n- التحقق من اتصال الإنترنت\n- تعديل النص المدخل\n- المحاولة لاحقًا"
