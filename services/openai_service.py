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

    def _initialize_client(self) -> OpenAI:
        """تهيئة العميل مع التحقق من المفتاح"""
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            logger.critical("OPENROUTER_API_KEY غير موجود في متغيرات البيئة")
            raise ValueError("API key is required")
        
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

    def _validate_response(self, response) -> bool:
        """التحقق من صحة الرد من API"""
        return (
            response and
            hasattr(response, 'choices') and
            len(response.choices) > 0 and
            hasattr(response.choices[0], 'message') and
            hasattr(response.choices[0].message, 'content')
        )

    def _clean_content(self, text: str, min_length: int) -> Tuple[Optional[str], bool]:
        """تنظيف المحتوى مع تقرير الجودة"""
        if not text:
            return None, False

        # إزالة العبارات الشخصية
        text = re.sub(r'يَا?\s?[اأإآ]?[صش]اح?ب?ي?\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bخو?يَ?ا?\b', '', text, flags=re.IGNORECASE)
        
        # التنظيف العام
        arabic_chars = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
        symbols = r'[!؟.,،؛:\-\#@_()\d\s]'
        emojis = r'[\U0001F300-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
        pattern = f'[{arabic_chars}{symbols}{emojis}]'
        
        cleaned = re.sub(f'[^{pattern}]', '', text)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return (cleaned, True) if len(cleaned) >= min_length else (None, False)

    def _generate_with_retry(self, prompt: str, system_msg: str, platform: str) -> Optional[str]:
        """إنشاء المحتوى مع إعادة المحاولة"""
        for attempt in range(self.max_attempts):
            try:
                start_time = time.time()
                
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
                            "content": system_msg + "\n\nتجنب:\n- مخاطبة القارئ مباشرة\n- المحتوى القصير\n- التكرار"
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.75,
                    max_tokens=800 if platform == 'لينكدإن' else 400,
                    timeout=self.timeout
                )

                if not self._validate_response(response):
                    logger.error(f"المحاولة {attempt + 1}: الرد غير صالح")
                    continue

                content = response.choices[0].message.content
                cleaned, is_valid = self._clean_content(content, self.min_lengths[platform])

                if is_valid and cleaned:
                    logger.info(f"تم إنشاء المحتوى بنجاح في {time.time()-start_time:.2f} ثانية")
                    return cleaned

                logger.warning(f"المحاولة {attempt + 1}: المحتوى غير صالح - الطول: {len(content) if content else 0}")

            except APIError as e:
                logger.error(f"خطأ API في المحاولة {attempt + 1}: {str(e)}")
                if attempt == self.max_attempts - 1:
                    raise
                time.sleep(2)  # إضافة تأخير بين المحاولات

            except Exception as e:
                logger.error(f"خطأ غير متوقع في المحاولة {attempt + 1}: {str(e)}")
                if attempt == self.max_attempts - 1:
                    raise

        return None

    def generate_response(self, user_input: str, platform: str, dialect: Optional[str] = None) -> str:
        """الدالة الرئيسية المحسنة"""
        if not user_input or not platform:
            return "⚠️ المدخلات غير صالحة"

        if platform not in self.emoji_sets:
            return f"⚠️ المنصة غير مدعومة. الخيارات: {', '.join(self.emoji_sets.keys())}"

        dialect_instructions = {
            "اليمنية": "استخدم لهجة يمنية أصيلة بكلمات مثل: عادك، شوف، قدك، تمام، طيب، ابسر، صنديد - بدون مخاطبة مباشرة",
            "المصرية": "استخدم لهجة مصرية بكلمات مثل: خلاص، يعني، قوي، جامد، تمام، يلا، اهو - بشكل طبيعي",
            "الشامية": "استخدم لهجة شامية بكلمات مثل: هلّق، شو القصة، كتير، منيح، بالهداوة - بأسلوب راقٍ",
            "المغربية": "استخدم لهجة مغربية بكلمات مثل: واخا، بزاف، دابا، زعما، مزيان - بشكل مناسب",
            "الخليجية": "استخدم لهجة خليجية بكلمات مثل: بعد، زين، مره، عاد، وايد - بأسلوب احترافي",
            "الفصحى المبسطة": "استخدم لغة عربية فصيحة مبسطة وسهلة الفهم"
        }

        system_msg = f"""أنت كاتب محتوى عربي محترف لـ {platform}. اكتب منشورًا عن:
"{user_input}"

المتطلبات الأساسية:
1. المحتوى مفصل وغني بالمعلومات
2. الطول الأدنى: {self.min_lengths[platform]} حرف
3. أضف {2 if platform == 'تويتر' else 3} إيموجي
4. استخدم أسلوبًا {dialect_instructions.get(dialect, 'احترافيًا')}"""

        try:
            content = self._generate_with_retry(
                prompt=f"أنشئ منشور {platform} عن: {user_input}",
                system_msg=system_msg,
                platform=platform
            )

            if content:
                return content

            return "⚠️ تعذر إنشاء محتوى يلبي المتطلبات. يرجى المحاولة لاحقًا"

        except Exception as e:
            logger.critical(f"فشل إنشاء المحتوى: {str(e)}")
            return "⚠️ حدث خطأ غير متوقع. يرجى التواصل مع الدعم الفني"

# تصدير الدالة
openai_service = OpenAIService()
generate_response = openai_service.generate_response
