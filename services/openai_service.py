import re
import logging
import os
import random
from openai import OpenAI
from typing import Optional, Dict, List, Union

# إعدادات التسجيل المتقدمة
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('content_generator.log', encoding='utf-8', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ArabicContentGenerator')

class ContentGenerator:
    def __init__(self):
        """تهيئة مولد المحتوى مع إعدادات API"""
        self.client = self._init_openai_client()
        self.emoji_sets = {
            'general': ["✨", "🌟", "💡", "🔥", "🎯", "📌", "🚀"],
            'twitter': ["🐦", "💬", "🔄", "❤️", "👏", "🔁", "👍"],
            'linkedin': ["💼", "📈", "🌐", "🤝", "🏆", "🔗", "📊"],
            'instagram': ["📸", "❤️", "👍", "😍", "🔥", "👀", "💫"]
        }
        self.max_retries = 3
        self.default_timeout = 30

    def _init_openai_client(self) -> OpenAI:
        """تهيئة عميل OpenAI مع التحقق من المفتاح"""
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            logger.error("API key not found in environment variables")
            raise ValueError("OPENROUTER_API_KEY is required")

        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

    def _clean_text(self, text: str, min_length: int = 20) -> Optional[str]:
        """
        تنظيف النص مع ضمان الحد الأدنى للطول
        Args:
            text: النص المراد تنظيفه
            min_length: الحد الأدنى لطول النص المقبول
        Returns:
            النص المنظف أو None إذا كان غير صالح
        """
        if not text or len(text.strip()) < min_length:
            return None

        try:
            # تعريف الأنماط المسموحة
            arabic_pattern = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
            symbols_pattern = r'[!؟.,،؛:\-\#@_()\d\s]'
            emoji_pattern = r'[\U0001F300-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
            
            # النمط الشامل
            allowed_pattern = f'{arabic_pattern}|{symbols_pattern}|{emoji_pattern}'
            
            # التنظيف
            cleaned = re.sub(f'[^{allowed_pattern}]', '', text)
            cleaned = re.sub(r'\s+', ' ', cleaned)  # إزالة المسافات الزائدة
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)  # تقليل الأسطر الفارغة
            return cleaned.strip()
        except Exception as e:
            logger.error(f"Text cleaning failed: {e}", exc_info=True)
            return None

    def _get_dialect_guide(self, dialect: str) -> str:
        """إرجاع إرشادات الكتابة باللهجة المطلوبة"""
        guides = {
            "المغربية": """
• الكلمات المميزة: واخا، بزاف، دابا، خويا، زعما، مزيان
• أمثلة:
  - "هاد التقنية غادي تغير بزاف طريقة العمل"
  - "مزيان باش نبداو نستافدو من هاد الإمكانيات"
""",
            "المصرية": """
• الكلمات المميزة: خلاص، يعني، قوي، جامد، تمام، يلا
• أمثلة:
  - "التعلم الذاتي بقى أساسي قوي في السوق دلوقتي"
  - "يعني إنت قادر تطور مهاراتك من البيت"
""",
            "الخليجية": """
• الكلمات المميزة: بعد، زين، مره، عاد، وايد
• أمثلة:
  - "التعلم الذاتي صار وايد مهم هالايام"
  - "عاد إنت قدها تتعلم كل شي بنفسك"
"""
        }
        return guides.get(dialect, "")

    def _generate_content(
        self,
        prompt: str,
        system_template: str,
        dialect: Optional[str] = None,
        max_tokens: int = 300,
        temperature: float = 0.7,
        min_length: int = 30
    ) -> Optional[str]:
        """الدالة الأساسية لإنشاء المحتوى"""
        style_note = self._get_dialect_guide(dialect) if dialect else ""
        system_message = system_template + style_note

        for attempt in range(self.max_retries):
            try:
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
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=self.default_timeout
                )

                content = response.choices[0].message.content
                cleaned = self._clean_text(content, min_length)

                if not cleaned:
                    logger.warning(f"Short content generated: {content[:100]}...")
                    continue

                # إضافة إيموجي إذا لم يكن موجودًا
                if not any(emoji in cleaned for emoji in self.emoji_sets['general']):
                    cleaned = f"{random.choice(self.emoji_sets['general'])} {cleaned}"

                return cleaned

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}", exc_info=True)
                if attempt == self.max_retries - 1:
                    raise

        return None

    def generate_twitter_post(
        self,
        topic: str,
        dialect: Optional[str] = None
    ) -> str:
        """
        إنشاء منشور تويتر محسن
        Args:
            topic: موضوع المنشور
            dialect: اللهجة المطلوبة (اختياري)
        Returns:
            نص المنشور أو رسالة خطأ
        """
        system_template = """\
أنت كاتب محتوى عربي محترف لتويتر. اكتب تغريدة عن:
"{topic}"

المتطلبات:
• ابدأ بجملة جذابة
• استخدم {dialect_instruction}
• الطول بين 20-280 حرفًا
• أضف 1-2 إيموجي
• لا تستخدم الهاشتاقات
• اجعل النص طبيعيًا وسلسًا"""

        try:
            content = self._generate_content(
                prompt=f"أنشئ تغريدة عن: {topic}",
                system_template=system_template.format(
                    topic=topic,
                    dialect_instruction=f"اللهجة {dialect}" if dialect else "الفصحى"
                ),
                dialect=dialect,
                max_tokens=280,
                temperature=0.75,
                min_length=20
            )

            return content or "⚠️ تعذر إنشاء المحتوى. يرجى المحاولة لاحقًا"

        except Exception as e:
            logger.error(f"Twitter post generation failed: {e}", exc_info=True)
            return "⚠️ حدث خطأ غير متوقع. يرجى المحاولة لاحقًا"

    def generate_linkedin_post(
        self,
        topic: str,
        dialect: Optional[str] = None
    ) -> str:
        """
        إنشاء منشور لينكدإن محسن
        Args:
            topic: موضوع المنشور
            dialect: اللهجة المطلوبة (اختياري)
        Returns:
            نص المنشور أو رسالة خطأ
        """
        system_template = """\
أنت خبير في كتابة المحتوى المهني للينكدإن. اكتب منشورًا عن:
"{topic}"

المتطلبات:
• ابدأ بجملة افتتاحية قوية
• استخدم {dialect_instruction}
• أضف 3 نقاط رئيسية
• اختتم بسؤال أو دعوة للتفاعل
• الطول بين 100-600 كلمة
• استخدم 2-3 إيموجي"""

        try:
            content = self._generate_content(
                prompt=f"أنشئ منشور لينكدإن عن: {topic}",
                system_template=system_template.format(
                    topic=topic,
                    dialect_instruction=f"اللهجة {dialect}" if dialect else "الفصحى"
                ),
                dialect=dialect,
                max_tokens=600,
                temperature=0.7,
                min_length=100
            )

            return content or "⚠️ تعذر إنشاء المحتوى. يرجى تعديل المدخلات"

        except Exception as e:
            logger.error(f"LinkedIn post generation failed: {e}", exc_info=True)
            return "⚠️ حدث خطأ غير متوقع"

    def generate_instagram_caption(
        self,
        topic: str,
        dialect: Optional[str] = None
    ) -> str:
        """
        إنشاء تعليق إنستغرام محسن
        Args:
            topic: موضوع التعليق
            dialect: اللهجة المطلوبة (اختياري)
        Returns:
            نص التعليق أو رسالة خطأ
        """
        system_template = """\
أنت مؤثر على إنستغرام. اكتب تعليقًا لصورة عن:
"{topic}"

المتطلبات:
• ابدأ بجملة جذابة
• استخدم {dialect_instruction}
• اجعل النص عاطفيًا أو ملهمًا
• الطول بين 50-300 حرف
• أضف 2-3 إيموجي
• لا تستخدم الهاشتاقات"""

        try:
            content = self._generate_content(
                prompt=f"أنشئ تعليق إنستغرام عن: {topic}",
                system_template=system_template.format(
                    topic=topic,
                    dialect_instruction=f"اللهجة {dialect}" if dialect else "الفصحى"
                ),
                dialect=dialect,
                max_tokens=300,
                temperature=0.8,
                min_length=50
            )

            return content or "⚠️ تعذر إنشاء المحتوى المناسب"

        except Exception as e:
            logger.error(f"Instagram caption generation failed: {e}", exc_info=True)
            return "⚠️ تعذر إنشاء المحتوى"

# مثال للاستخدام
if __name__ == "__main__":
    try:
        generator = ContentGenerator()
        
        # مثال لتغريدة تويتر
        tweet = generator.generate_twitter_post(
            "أهمية التعلم المستمر في التطوير المهني",
            dialect="المصرية"
        )
        print("🎯 التغريدة الناتجة:\n", tweet)
        
        # مثال لمنشور لينكدإن
        linkedin_post = generator.generate_linkedin_post(
            "كيفية بناء شبكة علاقات مهنية فعالة"
        )
        print("\n💼 منشور لينكدإن:\n", linkedin_post)
        
        # مثال لتعليق إنستغرام
        insta_caption = generator.generate_instagram_caption(
            "نصائح للتصوير الاحترافي بالهاتف",
            dialect="المغربية"
        )
        print("\n📸 تعليق إنستغرام:\n", insta_caption)
        
    except Exception as e:
        print("❌ حدث خطأ رئيسي:", str(e))
