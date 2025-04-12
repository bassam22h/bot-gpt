import re
import logging
import os
import random
from openai import OpenAI
from typing import Optional

# إعدادات التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('content_generator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ArabicContentGenerator')

class OpenAIService:
    def __init__(self):
        """تهيئة الخدمة بشكل آمن"""
        try:
            self.client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.getenv('OPENROUTER_API_KEY', '')
            )
            self._validate_client()
        except Exception as e:
            logger.critical(f"فشل تهيئة العميل: {str(e)}")
            self.client = None

        # إعدادات المحتوى
        self.platform_settings = {
            'تويتر': {
                'emojis': ["🐦", "💬", "🔄", "❤️", "👏"],
                'min_length': 50,
                'max_tokens': 280
            },
            'لينكدإن': {
                'emojis': ["💼", "📈", "🌐", "🤝", "🏆"],
                'min_length': 150,
                'max_tokens': 600
            },
            'إنستغرام': {
                'emojis': ["📸", "❤️", "👍", "😍", "🔥"],
                'min_length': 80,
                'max_tokens': 300
            }
        }

    def _validate_client(self):
        """التحقق من صحة العميل"""
        if not self.client or not os.getenv('OPENROUTER_API_KEY'):
            raise ValueError("إعدادات API غير صالحة")

    def _clean_content(self, text: str, platform: str) -> Optional[str]:
        """تنظيف المحتوى مع ضمان الجودة"""
        if not text or not isinstance(text, str):
            return None

        try:
            # التنظيف الأساسي
            text = re.sub(r'يَا?\s?[اأإآ]?[صش]اح?ب?ي?\b', '', text)
            text = re.sub(r'\bخو?يَ?ا?\b', '', text)
            
            # الاحتفاظ بالأحرف المسموحة فقط
            allowed_chars = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF!؟.,،؛:\-\#@_()\d\s\U0001F300-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
            cleaned = re.sub(f'[^{allowed_chars}]', '', text)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

            # التحقق من الطول الأدنى
            if len(cleaned) >= self.platform_settings[platform]['min_length']:
                return cleaned
            return None

        except Exception as e:
            logger.error(f"خطأ في تنظيف المحتوى: {str(e)}")
            return None

    def generate_response(self, user_input: str, platform: str, dialect: Optional[str] = None) -> str:
        """الدالة الرئيسية لإنشاء المحتوى"""
        try:
            # التحقق من الإعدادات الأولية
            if not self.client:
                logger.error("العميل غير مهيأ - تحقق من OPENROUTER_API_KEY")
                return "⚠️ الخدمة غير متاحة حالياً"

            if platform not in self.platform_settings:
                return f"⚠️ المنصة غير مدعومة. الخيارات: {', '.join(self.platform_settings.keys())}"

            # تعليمات النظام
            system_template = """أنت كاتب محتوى عربي محترف لـ {platform}. اكتب منشورًا عن:
"{topic}"

المتطلبات:
- المحتوى مفيد وجذاب
- الطول المناسب للمنصة
- أسلوب {dialect_instruction}
- {emoji_count} إيموجي مناسبة"""

            dialect_instruction = f"لهجة {dialect}" if dialect else "فصيح"
            settings = self.platform_settings[platform]

            try:
                response = self.client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": os.getenv('SITE_URL', 'https://default.com'),
                        "X-Title": os.getenv('SITE_NAME', 'Content Generator'),
                    },
                    model="google/gemini-2.0-flash-thinking-exp:free",
                    messages=[
                        {
                            "role": "system",
                            "content": system_template.format(
                                platform=platform,
                                topic=user_input,
                                dialect_instruction=dialect_instruction,
                                emoji_count="2-3"
                            )
                        },
                        {
                            "role": "user",
                            "content": f"أنشئ منشور {platform} عن: {user_input}"
                        }
                    ],
                    temperature=0.7,
                    max_tokens=settings['max_tokens'],
                    timeout=30
                )
            except Exception as api_error:
                logger.error(f"فشل طلب API: {str(api_error)}")
                return "⚠️ فشل الاتصال بالخدمة. يرجى المحاولة لاحقًا"

            # التحقق من صحة الرد
            if response is None:
                logger.error("رد API فارغ")
                raise ValueError("فشل الاتصال بالخدمة: لا يوجد رد من API")

            if not hasattr(response, 'choices'):
                logger.error(f"رد API غير صالح: {str(response)}")
                raise ValueError("رد API غير صالح أو لا يحتوي على خيارات")

            if not response.choices:
                logger.error("رد API لا يحتوي على خيارات")
                raise ValueError("رد API فارغ (لا توجد خيارات)")

            # معالجة الرد
            content = response.choices[0].message.content
            cleaned_content = self._clean_content(content, platform)

            if not cleaned_content:
                logger.error(f"المحتوى الناتج غير صالح: {content}")
                raise ValueError("المحتوى الناتج غير صالح")

            # إضافة إيموجي إذا لزم الأمر
            if not any(emoji in cleaned_content for emoji in settings['emojis']):
                cleaned_content = f"{random.choice(settings['emojis'])} {cleaned_content}"

            return cleaned_content

        except ValueError as ve:
            logger.error(f"خطأ في القيمة: {str(ve)}")
            return f"⚠️ {str(ve)}"
        except Exception as e:
            logger.error(f"فشل إنشاء المحتوى: {str(e)}", exc_info=True)
            return "⚠️ حدث خطأ أثناء إنشاء المحتوى. يرجى المحاولة لاحقًا"

# تهيئة الخدمة وتصدير الدالة
try:
    openai_service = OpenAIService()
    generate_response = openai_service.generate_response
except Exception as e:
    logger.critical(f"فشل تهيئة الخدمة: {str(e)}", exc_info=True)
    generate_response = lambda *args, **kwargs: "⚠️ الخدمة غير متاحة حالياً"
