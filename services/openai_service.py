import re
import logging
import os
import random
from openai import OpenAI
from typing import Optional, Dict, Callable

# إعدادات التسجيل المتقدمة
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_errors.log', encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ArabicContentGenerator')

class ContentGenerator:
    def __init__(self):
        self.client = self._initialize_client()
        self.EMOJI_SETS = {
            'default': ["✨", "🌟", "💡", "🔥", "🎯"],
            'twitter': ["🐦", "💬", "🔄", "❤️", "👏"],
            'linkedin': ["💼", "📈", "🌐", "🤝", "🏆"],
            'instagram': ["📸", "❤️", "👍", "😍", "🔥"]
        }

    def _initialize_client(self) -> OpenAI:
        """تهيئة عميل OpenAI مع التحقق من المفتاح"""
        API_KEY = os.getenv('OPENROUTER_API_KEY')
        if not API_KEY:
            logger.critical("OPENROUTER_API_KEY غير موجود في متغيرات البيئة")
            raise ValueError("API key is required")

        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=API_KEY,
        )

    def _clean_content(self, text: str, min_length: int = 30) -> Optional[str]:
        """تنظيف المحتوى مع ضمان طول أدنى وتحسين الأداء"""
        if not text or len(str(text).strip()) < min_length:
            return None

        try:
            # أنماط موسعة للأحرف المسموحة
            patterns = [
                r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]',  # عربي
                r'[!؟.,،؛:\n\-#@_()\d]',  # رموز
                r'[\U0001F300-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'  # إيموجي
            ]
            
            # تنظيف متقدم مع الاحتفاظ بالمسافات المناسبة
            cleaned = re.sub(fr'[^{}]'.format(''.join(patterns)), '', str(text))
            cleaned = re.sub(r'\s+', ' ', cleaned)  # normalize spaces
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            return cleaned.strip()
        except Exception as e:
            logger.error(f"فشل تنظيف النص: {str(e)}", exc_info=True)
            return None

    def _generate_with_retry(
        self,
        prompt: str,
        system_message: str,
        dialect: Optional[str] = None,
        max_tokens: int = 350,
        temperature: float = 0.7,
        min_length: int = 50,
        max_retries: int = 3
    ) -> Optional[str]:
        """دالة أساسية محسنة مع إعادة المحاولة وضمان الجودة"""
        style_note = self._get_dialect_guide(dialect) if dialect else ""
        full_system_msg = f"{system_message}\n{style_note}"

        for attempt in range(max_retries):
            try:
                logger.info(f"المحاولة {attempt + 1} لإنشاء المحتوى")

                response = self.client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": os.getenv('SITE_URL', 'https://default.com'),
                        "X-Title": os.getenv('SITE_NAME', 'Arabic Content Generator'),
                    },
                    extra_body={
                        "ensure_quality": True,
                        "min_length": min_length
                    },
                    model="google/gemini-2.0-flash-thinking-exp:free",
                    messages=[
                        {"role": "system", "content": full_system_msg},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=45.0
                )

                content = response.choices[0].message.content
                cleaned = self._clean_content(content, min_length)

                if not cleaned:
                    logger.warning(f"الناتج قصير: {content[:100]}...")
                    continue

                # إضافة إيموجي تلقائي إذا لزم الأمر
                if not any(emoji in cleaned for emoji in self.EMOJI_SETS['default']):
                    cleaned = f"{random.choice(self.EMOJI_SETS['default'])} {cleaned}"

                return cleaned

            except Exception as e:
                logger.error(f"خطأ في المحاولة {attempt + 1}: {str(e)}", exc_info=True)
                if attempt == max_retries - 1:
                    raise

        return None

    def _get_dialect_guide(self, dialect: str) -> str:
        """إرشادات اللهجات مع أمثلة موسعة"""
        guides = {
            "المغربية": """\
- الكلمات المفتاحية: واخّا، بزاف، دابا، خويا، زعما، مزيان
- أمثلة: 
  * "هاد الشيء عندو قيمة بزاف فالعصر الرقمي"
  * "مزيان باش نبداو نستافدو من هاد التقنيات"
""",
            "المصرية": """\
- الكلمات المفتاحية: يلا، جامد، كده، خلاص، يعني، قوي
- أمثلة:
  * "التعلم الذاتي بقى أساسي قوي في السنوات الأخيرة"
  * "كده يعني إنت قادر تطور من نفسك من البيت"
""",
            "الخليجية": """\
- الكلمات المفتاحية: بعد، زين، مره، عاد، وايد
- أمثلة:
  * "التعلم الذاتي صار وايد مهم هالايام"
  * "عاد إنت قدها تتعلم كل شي بنفسك"
"""
        }
        return guides.get(dialect, "")

    def generate_twitter_post(
        self,
        topic: str,
        dialect: Optional[str] = None,
        max_retries: int = 3
    ) -> str:
        """إنشاء تغريدة محسنة مع ضمان الجودة"""
        system_template = """\
أنت كاتب محتوى عربي محترف لموقع تويتر. اكتب تغريدة عن:
"{topic}"

المتطلبات:
1. ابدأ بجملة جذابة
2. استخدم {dialect_instruction}
3. الطول بين 20-280 حرفًا
4. أضف 1-2 إيموجي مناسب
5. لا تستخدم الهاشتاقات
6. اجعل النص سلسًا وطبيعيًا"""

        dialect_instruction = f"اللهجة {dialect}" if dialect else "الفصحى"
        
        try:
            content = self._generate_with_retry(
                prompt=f"أنشئ تغريدة عن: {topic}",
                system_message=system_template.format(
                    topic=topic,
                    dialect_instruction=dialect_instruction
                ),
                dialect=dialect,
                max_tokens=280,
                temperature=0.75,
                min_length=20,
                max_retries=max_retries
            )

            if not content:
                return "⚠️ لم يتم إنشاء المحتوى. يرجى المحاولة مرة أخرى"

            # تطبيق التنسيق النهائي
            return content[:280]  # تأكيد الحد الأقصى لطول التغريدة

        except Exception as e:
            logger.error(f"فشل إنشاء التغريدة: {str(e)}", exc_info=True)
            return "⚠️ حدث خطأ أثناء إنشاء المحتوى. يرجى المحاولة لاحقًا"

    def generate_linkedin_post(
        self,
        topic: str,
        dialect: Optional[str] = None,
        max_retries: int = 2
    ) -> str:
        """إنشاء منشور لينكدإن محسن"""
        system_template = """\
أنت خبير في كتابة المحتوى المهني للينكدإن. اكتب منشورًا عن:
"{topic}"

المتطلبات:
1. ابدأ بجملة افتتاحية قوية
2. استخدم {dialect_instruction}
3. أضف 3 نقاط رئيسية
4. اختتم بدعوة للتفاعل أو سؤال مفتوح
5. الطول بين 100-600 كلمة
6. استخدم 2-3 إيموجي مناسبة"""

        try:
            content = self._generate_with_retry(
                prompt=f"أنشئ منشور لينكدإن عن: {topic}",
                system_message=system_template.format(
                    topic=topic,
                    dialect_instruction="اللهجة " + dialect if dialect else "الفصحى"
                ),
                dialect=dialect,
                max_tokens=600,
                temperature=0.7,
                min_length=100,
                max_retries=max_retries
            )

            return content or "⚠️ لم يتم إنشاء المحتوى. يرجى تعديل المدخلات"

        except Exception as e:
            logger.error(f"فشل إنشاء منشور لينكدإن: {str(e)}", exc_info=True)
            return "⚠️ حدث خطأ غير متوقع"

    def generate_instagram_post(
        self,
        topic: str,
        dialect: Optional[str] = None,
        max_retries: int = 3
    ) -> str:
        """إنشاء منشور إنستغرام محسن"""
        system_template = """\
أنت مؤثر على إنستغرام. اكتب تعليقًا لصورة عن:
"{topic}"

المتطلبات:
1. ابدأ بجملة جذابة
2. استخدم {dialect_instruction}
3. اجعل النص عاطفيًا أو ملهمًا
4. الطول بين 50-300 حرف
5. أضف 2-3 إيموجي
6. لا تستخدم الهاشتاقات"""

        try:
            content = self._generate_with_retry(
                prompt=f"أنشئ منشور إنستغرام عن: {topic}",
                system_message=system_template.format(
                    topic=topic,
                    dialect_instruction="اللهجة " + dialect if dialect else "الفصحى"
                ),
                dialect=dialect,
                max_tokens=300,
                temperature=0.8,
                min_length=50,
                max_retries=max_retries
            )

            return content or "⚠️ لم يتم إنشاء المحتوى المناسب"

        except Exception as e:
            logger.error(f"فشل إنشاء منشور إنستغرام: {str(e)}", exc_info=True)
            return "⚠️ تعذر إنشاء المحتوى"

# واجهة الاستخدام البسيطة
if __name__ == "__main__":
    generator = ContentGenerator()
    
    # مثال للاستخدام
    try:
        tweet = generator.generate_twitter_post(
            "أهمية التعلم الذاتي في العصر الرقمي",
            dialect="المصرية"
        )
        print("التغريدة الناتجة:\n", tweet)
        
        linkedin_post = generator.generate_linkedin_post(
            "كيفية بناء شبكة علاقات مهنية فعالة"
        )
        print("\nمنشور لينكدإن:\n", linkedin_post)
        
    except Exception as e:
        print("حدث خطأ رئيسي:", str(e))
