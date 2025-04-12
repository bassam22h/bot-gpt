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
            logger.critical(f"فشل تهيئة العميل: {str(e)}", exc_info=True)
            self.client = None

        # إعدادات المحتوى
        self.platform_settings = {
            'تويتر': {
                'emojis': ["🐦", "💬", "🔄", "❤️", "👏"],
                'min_length': 30,  # تم تخفيض الحد الأدنى
                'max_tokens': 280
            },
            'لينكدإن': {
                'emojis': ["💼", "📈", "🌐", "🤝", "🏆"],
                'min_length': 100,  # تم تخفيض الحد الأدنى
                'max_tokens': 600
            },
            'إنستغرام': {
                'emojis': ["📸", "❤️", "👍", "😍", "🔥"],
                'min_length': 50,  # تم تخفيض الحد الأدنى
                'max_tokens': 300
            }
        }

    def _validate_client(self):
        """التحقق من صحة العميل"""
        if not self.client or not os.getenv('OPENROUTER_API_KEY'):
            raise ValueError("إعدادات API غير صالحة")

    def _clean_content(self, text: str, platform: str) -> Optional[str]:
        """تنظيف المحتوى مع ضمان الجودة"""
        try:
            if not text or not isinstance(text, str):
                logger.warning(f"نص الإدخال غير صالح: {text}")
                return None

            # التنظيف الأساسي
            text = re.sub(r'يَا?\s?[اأإآ]?[صش]اح?ب?ي?\b', '', text)
            text = re.sub(r'\bخو?يَ?ا?\b', '', text)
            
            # الاحتفاظ بالأحرف المسموحة فقط
            allowed_chars = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF!؟.,،؛:\-\#@_()\d\s\U0001F300-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
            cleaned = re.sub(f'[^{allowed_chars}]', '', text)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()

            # تسجيل المحتوى قبل التحقق من الطول
            logger.debug(f"المحتوى بعد التنظيف وقبل التحقق: {cleaned}")

            # تعديل شرط الطول ليكون أكثر مرونة
            min_len = self.platform_settings[platform]['min_length']
            if len(cleaned) >= min_len:
                return cleaned
            else:
                logger.warning(f"المحتوى قصير جدًا ({len(cleaned)} حرفًا)، المطلوب {min_len}")
                return None

        except Exception as e:
            logger.error(f"خطأ في التنظيف: {str(e)}", exc_info=True)
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
                logger.error(f"فشل طلب API: {str(api_error)}", exc_info=True)
                return "⚠️ فشل الاتصال بالخدمة. يرجى المحاولة لاحقًا"

            # التحقق من صحة الرد
            if response is None:
                logger.error("رد API فارغ")
                return "⚠️ لا يوجد رد من الخدمة"

            if not hasattr(response, 'choices'):
                logger.error(f"رد API غير صالح: {str(response)}")
                return "⚠️ هيكل الرد غير متوقع"

            if not response.choices:
                logger.error("رد API لا يحتوي على خيارات")
                return "⚠️ لا توجد خيارات متاحة في الرد"

            # معالجة الرد
            content = response.choices[0].message.content
            logger.debug(f"المحتوى الخام من API: {content}")

            cleaned_content = self._clean_content(content, platform)
            if not cleaned_content:
                logger.error(f"المحتوى الناتج غير صالح:\nالخام: {content}")
                return "⚠️ المحتوى الناتج لا يلبي الشروط المطلوبة"

            # إضافة إيموجي إذا لزم الأمر
            if not any(emoji in cleaned_content for emoji in settings['emojis']):
                cleaned_content = f"{random.choice(settings['emojis'])} {cleaned_content}"

            return cleaned_content

        except Exception as e:
            logger.error(f"خطأ غير متوقع: {str(e)}", exc_info=True)
            return "⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقًا"

# تهيئة الخدمة وتصدير الدالة
try:
    openai_service = OpenAIService()
    generate_response = openai_service.generate_response
except Exception as e:
    logger.critical(f"فشل تهيئة الخدمة: {str(e)}", exc_info=True)
    generate_response = lambda *args, **kwargs: "⚠️ الخدمة غير متاحة حالياً"
