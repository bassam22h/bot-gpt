import re
import logging
import os
import random
import time
from openai import OpenAI, APIError
from typing import Optional, Tuple

logger = logging.getLogger('ArabicContentGenerator')

class OpenAIService:
    def __init__(self):
        self.client = self._initialize_client()
        self.emoji_sets = {
            'تويتر': ["🐦", "💬", "🔄", "❤️", "👏"],
            'لينكدإن': ["💼", "📈", "🌐", "🤝", "🏆"],
            'إنستغرام': ["📸", "❤️", "👍", "😍", "🔥"]
        }
        self.min_lengths = {
            'تويتر': 50,
            'لينكدإن': 200,
            'إنستغرام': 80
        }
        self.max_attempts = 3
        self.timeout = 60

    def _initialize_client(self) -> Optional[OpenAI]:
        """تهيئة العميل مع معالجة الأخطاء الشاملة"""
        try:
            api_key = os.getenv('OPENROUTER_API_KEY')
            if not api_key:
                logger.error("OPENROUTER_API_KEY غير موجود")
                return None
            
            return OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
        except Exception as e:
            logger.critical(f"فشل تهيئة العميل: {str(e)}")
            return None

    def _validate_content(self, content: Optional[str], min_length: int) -> Tuple[Optional[str], bool]:
        """التحقق من صحة المحتوى بشكل شامل"""
        if not content or not isinstance(content, str):
            return None, False

        try:
            # إزالة العبارات الشخصية
            content = re.sub(r'يَا?\s?[اأإآ]?[صش]اح?ب?ي?\b', '', content, flags=re.IGNORECASE)
            content = re.sub(r'\bخو?يَ?ا?\b', '', content, flags=re.IGNORECASE)
            
            # التنظيف العام
            arabic_chars = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
            symbols = r'[!؟.,،؛:\-\#@_()\d\s]'
            emojis = r'[\U0001F300-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
            pattern = f'[{arabic_chars}{symbols}{emojis}]'
            
            cleaned = re.sub(f'[^{pattern}]', '', content)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            
            if len(cleaned) >= min_length:
                return cleaned, True
            return None, False
            
        except Exception as e:
            logger.error(f"خطأ في التحقق من المحتوى: {str(e)}")
            return None, False

    def _generate_safe_content(self, prompt: str, system_msg: str, platform: str) -> Optional[str]:
        """إنشاء محتوى مع معالجة شاملة للأخطاء"""
        if not self.client:
            logger.error("عميل OpenAI غير مهيأ")
            return None

        for attempt in range(self.max_attempts):
            try:
                start_time = time.time()
                logger.info(f"المحاولة {attempt + 1} لإنشاء المحتوى لـ {platform}")
                
                response = self.client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": os.getenv('SITE_URL', 'https://default.com'),
                        "X-Title": os.getenv('SITE_NAME', 'Content Generator'),
                    },
                    extra_body={
                        "length_penalty": 1.5,
                        "min_length": self.min_lengths[platform]
                    },
                    model="google/gemini-2.0-flash-thinking-exp:free",
                    messages=[
                        {
                            "role": "system", 
                            "content": f"{system_msg}\n\nتأكد من:\n- الطول الكافي\n- الجودة العالية\n- عدم وجود أخطاء"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.75,
                    max_tokens=800 if platform == 'لينكدإن' else 400,
                    timeout=self.timeout
                )

                if not response or not hasattr(response, 'choices') or not response.choices:
                    logger.warning(f"المحاولة {attempt + 1}: استجابة API غير صالحة")
                    continue

                content = response.choices[0].message.content if hasattr(response.choices[0].message, 'content') else None
                if not content:
                    logger.warning(f"المحاولة {attempt + 1}: محتوى فارغ")
                    continue

                logger.info(f"تم استلام رد بنجاح في {time.time()-start_time:.2f} ثانية")
                return content

            except APIError as e:
                logger.error(f"خطأ API في المحاولة {attempt + 1}: {str(e)}")
                if attempt == self.max_attempts - 1:
                    raise
                time.sleep(2)

            except Exception as e:
                logger.error(f"خطأ غير متوقع في المحاولة {attempt + 1}: {str(e)}")
                if attempt == self.max_attempts - 1:
                    raise

        return None

    def generate_response(self, user_input: str, platform: str, dialect: Optional[str] = None) -> str:
        """الدالة الرئيسية مع ضمانات إضافية"""
        try:
            # التحقق الأولي
            if not user_input or not platform:
                return "⚠️ المدخلات غير صالحة"

            if not self.client:
                return "⚠️ حدث خطأ في الإعدادات. يرجى التواصل مع الدعم"

            if platform not in self.emoji_sets:
                return f"⚠️ المنصة غير مدعومة. الخيارات: {', '.join(self.emoji_sets.keys())}"

            # تعليمات اللهجة
            dialect_guides = {
                "اليمنية": "استخدم لهجة يمنية أصيلة بكلمات مثل: عادك، شوف، قدك، تمام، طيب، ابسر - بدون مخاطبة مباشرة",
                "المصرية": "استخدم لهجة مصرية بكلمات مثل: خلاص، يعني، قوي، جامد، تمام، يلا - بشكل طبيعي",
                "الشامية": "استخدم لهجة شامية بكلمات مثل: هلّق، شو القصة، كتير، منيح - بأسلوب راقٍ",
                "المغربية": "استخدم لهجة مغربية بكلمات مثل: واخا، بزاف، دابا، زعما - بشكل مناسب",
                "الخليجية": "استخدم لهجة خليجية بكلمات مثل: بعد، زين، مره، عاد - بأسلوب احترافي",
                "الفصحى المبسطة": "استخدم لغة عربية فصيحة مبسطة وسهلة الفهم"
            }

            system_msg = f"""أنت كاتب محتوى عربي محترف لـ {platform}. اكتب منشورًا عن:
"{user_input}"

المتطلبات الأساسية:
1. المحتوى مفصل وغني بالمعلومات
2. الطول الأدنى: {self.min_lengths[platform]} حرف
3. أضف {2 if platform == 'تويتر' else 3} إيموجي
4. استخدم أسلوبًا {dialect_guides.get(dialect, 'احترافيًا')}"""

            # إنشاء المحتوى
            content = self._generate_safe_content(
                prompt=f"أنشئ منشور {platform} عن: {user_input}",
                system_msg=system_msg,
                platform=platform
            )

            if not content:
                return "⚠️ فشل إنشاء المحتوى. يرجى المحاولة لاحقًا"

            # التحقق من الجودة
            cleaned, is_valid = self._validate_content(content, self.min_lengths[platform])
            if not is_valid or not cleaned:
                return "⚠️ المحتوى الناتج غير صالح. يرجى المحاولة مرة أخرى"

            # إضافة إيموجي إذا لزم
            if not any(emoji in cleaned for emoji in self.emoji_sets[platform]):
                cleaned = f"{random.choice(self.emoji_sets[platform])} {cleaned}"

            return cleaned

        except Exception as e:
            logger.critical(f"فشل إنشاء المحتوى: {str(e)}", exc_info=True)
            return "⚠️ حدث خطأ غير متوقع. يرجى التواصل مع الدعم الفني"

# تصدير الدالة بشكل آمن
try:
    openai_service = OpenAIService()
    generate_response = openai_service.generate_response if openai_service.client else lambda *args, **kwargs: "⚠️ الخدمة غير متاحة حالياً"
except Exception as e:
    logger.critical(f"فشل تهيئة الخدمة: {str(e)}")
    generate_response = lambda *args, **kwargs: "⚠️ الخدمة غير متاحة حالياً"
