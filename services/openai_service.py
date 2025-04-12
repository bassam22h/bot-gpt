import re
import logging
import os
import random
from openai import OpenAI
from typing import Optional

# إعدادات التسجيل
logging.basicConfig(
    level=logging.DEBUG,  # تغيير إلى DEBUG لمزيد من التفاصيل
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
            logger.critical(f"فشل تهيئة العميل: {str(e)}", exc_info=True)
            self.client = None

        # إعدادات المحتوى المعدلة
        self.platform_settings = {
            'تويتر': {
                'emojis': ["🐦", "💬", "🔄", "❤️", "👏"],
                'min_length': 20,  # تخفيض كبير في الحد الأدنى
                'max_tokens': 280
            },
            'لينكدإن': {
                'emojis': ["💼", "📈", "🌐", "🤝", "🏆"],
                'min_length': 50,
                'max_tokens': 600
            },
            'إنستغرام': {
                'emojis': ["📸", "❤️", "👍", "😍", "🔥"],
                'min_length': 30,
                'max_tokens': 300
            }
        }

    def _validate_client(self):
        """التحقق من صحة العميل"""
        if not self.client or not os.getenv('OPENROUTER_API_KEY'):
            raise ValueError("إعدادات API غير صالحة")

    def _clean_content(self, text: str, platform: str) -> Optional[str]:
        """دالة تنظيف محسنة مع تسجيل تفصيلي"""
        try:
            if not text or not isinstance(text, str) or text.isspace():
                logger.warning(f"نص الإدخال غير صالح: {repr(text)}")
                return None

            # تسجيل المحتوى الأصلي
            logger.debug(f"المحتوى قبل التنظيف: {repr(text)}")

            # التنظيف الأساسي
            text = re.sub(r'يَا?\s?[اأإآ]?[صش]اح?ب?ي?\b', '', text)
            text = re.sub(r'\bخو?يَ?ا?\b', '', text)
            
            # التنظيف المرن
            allowed_chars = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF!؟.,،؛:\-\#@_()\d\s\U0001F300-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
            cleaned = re.sub(f'[^{allowed_chars}]', '', text)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

            # التحقق من الطول
            min_len = self.platform_settings[platform]['min_length']
            if len(cleaned) < min_len:
                logger.warning(f"المحتوى قصير ({len(cleaned)} حرفًا)، المسموح: {min_len}")
                return None

            logger.debug(f"المحتوى بعد التنظيف: {repr(cleaned)}")
            return cleaned

        except Exception as e:
            logger.error(f"خطأ في التنظيف: {str(e)}", exc_info=True)
            return None

    def generate_response(self, user_input: str, platform: str, dialect: Optional[str] = None) -> str:
        """الدالة الرئيسية مع تعزيز معالجة الأخطاء"""
        try:
            # التحقق من الإعدادات الأولية
            if not self.client:
                logger.error("العميل غير مهيأ - تحقق من OPENROUTER_API_KEY")
                return "⚠️ الخدمة غير متاحة حالياً"

            if platform not in self.platform_settings:
                return f"⚠️ المنصة غير مدعومة. الخيارات: {', '.join(self.platform_settings.keys())}"

            # تعليمات النظام المحسنة
            system_template = """أنت كاتب محتوى عربي محترف لـ {platform}. اكتب منشورًا عن:
"{topic}"

المتطلبات:
- المحتوى مفيد وجذاب
- الطول بين {min_length}-{max_tokens} حرفًا
- أسلوب {dialect_instruction}
- استخدم 2-3 إيموجي مناسبة
- تجنب العبارات غير الرسمية"""

            settings = self.platform_settings[platform]
            dialect_instruction = f"لهجة {dialect}" if dialect else "فصيح"

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
                                min_length=settings['min_length'],
                                max_tokens=settings['max_tokens']
                            )
                        },
                        {
                            "role": "user",
                            "content": f"أنشئ منشور {platform} عن: {user_input}"
                        }
                    ],
                    temperature=0.8,  # زيادة الإبداع قليلاً
                    max_tokens=settings['max_tokens'],
                    timeout=45  # زيادة وقت الانتظار
                )
            except Exception as api_error:
                logger.error(f"فشل طلب API: {str(api_error)}", exc_info=True)
                return "⚠️ فشل الاتصال بالخدمة. يرجى المحاولة لاحقًا"

            # معالجة الرد بشكل أقوى
            if not response or not hasattr(response, 'choices') or not response.choices:
                logger.error(f"رد API غير صالح: {str(response)}")
                return "⚠️ حصلنا على رد غير متوقع من الخدمة"

            content = getattr(response.choices[0].message, 'content', None)
            if not content:
                logger.error("المحتوى المُرجع فارغ")
                return "⚠️ لم يتم إنشاء أي محتوى"

            logger.debug(f"المحتوى الخام: {repr(content)}")

            # التنظيف والتحقق
            cleaned_content = self._clean_content(content, platform)
            if not cleaned_content:
                logger.error(f"فشل التنظيف للمحتوى: {repr(content)}")
                return "⚠️ المحتوى المُنشأ لا يلبي معايير الجودة"

            # إضافة إيموجي تلقائي
            if not any(emoji in cleaned_content for emoji in settings['emojis']):
                emoji = random.choice(settings['emojis'])
                cleaned_content = f"{emoji} {cleaned_content}"
                logger.debug(f"تمت إضافة إيموجي: {emoji}")

            return cleaned_content

        except Exception as e:
            logger.error(f"خطأ غير متوقع: {str(e)}", exc_info=True)
            return "⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقًا"

# تهيئة الخدمة
try:
    openai_service = OpenAIService()
    generate_response = openai_service.generate_response
except Exception as e:
    logger.critical(f"فشل تهيئة الخدمة: {str(e)}", exc_info=True)
    generate_response = lambda *args, **kwargs: "⚠️ الخدمة غير متاحة حالياً"
