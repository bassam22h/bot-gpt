import re
import logging
import os
import random
from openai import OpenAI
from typing import Optional, Dict, List, Union

# إعدادات التسجيل
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
        self.client = self._init_client()
        self.emoji_sets = {
            'general': ["✨", "🌟", "💡", "🔥", "🎯"],
            'twitter': ["🐦", "💬", "🔄", "❤️", "👏"],
            'linkedin': ["💼", "📈", "🌐", "🤝", "🏆"],
            'instagram': ["📸", "❤️", "👍", "😍", "🔥"]
        }

    def _init_client(self) -> OpenAI:
        """تهيئة عميل OpenAI"""
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

    def _clean_text(self, text: str, min_length: int = 20) -> Optional[str]:
        """تنظيف النص مع ضمان الحد الأدنى للطول"""
        if not text or len(text.strip()) < min_length:
            return None

        try:
            arabic_chars = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
            symbols = r'[!؟.,،؛:\-\#@_()\d\s]'
            emojis = r'[\U0001F300-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
            pattern = f'[{arabic_chars}{symbols}{emojis}]'
            
            cleaned = re.sub(f'[^{pattern}]', '', text)
            cleaned = re.sub(r'\s+', ' ', cleaned)
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            return cleaned.strip()
        except Exception as e:
            logger.error(f"Text cleaning failed: {e}")
            return None

    def _get_dialect_guide(self, dialect: str) -> str:
        """إرشادات اللهجات"""
        guides = {
            "المغربية": "استخدم: واخا، بزاف، دابا، خويا، زعما، مزيان",
            "المصرية": "استخدم: خلاص، يعني، قوي، جامد، تمام، يلا",
            "الخليجية": "استخدم: بعد، زين، مره، عاد، وايد"
        }
        return guides.get(dialect, "")

    def generate_response(
        self,
        user_input: str,
        platform: str,
        dialect: Optional[str] = None,
        max_retries: int = 3
    ) -> str:
        """
        الدالة الرئيسية لإنشاء المحتوى (التي تحل محل generate_response القديمة)
        Args:
            user_input: نص الإدخال
            platform: المنصة (تويتر، لينكدإن، إنستغرام)
            dialect: اللهجة المطلوبة
            max_retries: عدد المحاولات
        Returns:
            النص المولد أو رسالة خطأ
        """
        platform_handlers = {
            "تويتر": self._generate_twitter_post,
            "لينكدإن": self._generate_linkedin_post,
            "إنستغرام": self._generate_instagram_post
        }

        if platform not in platform_handlers:
            return f"المنصة غير مدعومة. الخيارات: {', '.join(platform_handlers.keys())}"

        for attempt in range(max_retries):
            try:
                content = platform_handlers[platform](user_input, dialect)
                if content:
                    return content
            except Exception as e:
                logger.error(f"المحاولة {attempt + 1} فشلت: {e}")

        return "⚠️ فشل إنشاء المحتوى. يرجى المحاولة لاحقًا"

    def _generate_twitter_post(
        self,
        topic: str,
        dialect: Optional[str] = None
    ) -> Optional[str]:
        """إنشاء تغريدة تويتر"""
        system_msg = f"""\
اكتب تغريدة عن: "{topic}"
- استخدم {f"اللهجة {dialect}" if dialect else "الفصحى"}
- الطول بين 20-280 حرفًا
- أضف 1-2 إيموجي"""
        
        if dialect:
            system_msg += f"\n{self._get_dialect_guide(dialect)}"

        try:
            response = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": os.getenv('SITE_URL', 'https://default.com'),
                    "X-Title": os.getenv('SITE_NAME', 'Content Generator'),
                },
                extra_body={},
                model="google/gemini-2.0-flash-thinking-exp:free",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": f"أنشئ تغريدة عن: {topic}"}
                ],
                temperature=0.7,
                max_tokens=280,
                timeout=30
            )
            content = response.choices[0].message.content
            return self._clean_text(content, 20)
        except Exception as e:
            logger.error(f"فشل إنشاء تغريدة: {e}")
            return None

    def _generate_linkedin_post(
        self,
        topic: str,
        dialect: Optional[str] = None
    ) -> Optional[str]:
        """إنشاء منشور لينكدإن"""
        system_msg = f"""\
اكتب منشور لينكدإن عن: "{topic}"
- استخدم {f"اللهجة {dialect}" if dialect else "الفصحى"}
- الطول بين 100-600 كلمة
- أضف 2-3 إيموجي"""
        
        if dialect:
            system_msg += f"\n{self._get_dialect_guide(dialect)}"

        try:
            response = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": os.getenv('SITE_URL', 'https://default.com'),
                    "X-Title": os.getenv('SITE_NAME', 'Content Generator'),
                },
                extra_body={},
                model="google/gemini-2.0-flash-thinking-exp:free",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": f"أنشئ منشور لينكدإن عن: {topic}"}
                ],
                temperature=0.7,
                max_tokens=600,
                timeout=45
            )
            content = response.choices[0].message.content
            return self._clean_text(content, 100)
        except Exception as e:
            logger.error(f"فشل إنشاء منشور لينكدإن: {e}")
            return None

    def _generate_instagram_post(
        self,
        topic: str,
        dialect: Optional[str] = None
    ) -> Optional[str]:
        """إنشاء منشور إنستغرام"""
        system_msg = f"""\
اكتب منشور إنستغرام عن: "{topic}"
- استخدم {f"اللهجة {dialect}" if dialect else "الفصحى"}
- الطول بين 50-300 حرف
- أضف 2-3 إيموجي"""
        
        if dialect:
            system_msg += f"\n{self._get_dialect_guide(dialect)}"

        try:
            response = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": os.getenv('SITE_URL', 'https://default.com'),
                    "X-Title": os.getenv('SITE_NAME', 'Content Generator'),
                },
                extra_body={},
                model="google/gemini-2.0-flash-thinking-exp:free",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": f"أنشئ منشور إنستغرام عن: {topic}"}
                ],
                temperature=0.8,
                max_tokens=300,
                timeout=30
            )
            content = response.choices[0].message.content
            return self._clean_text(content, 50)
        except Exception as e:
            logger.error(f"فشل إنشاء منشور إنستغرام: {e}")
            return None

# واجهة استخدام مبسطة
if __name__ == "__main__":
    generator = ContentGenerator()
    
    # مثال للاستخدام
    try:
        # إنشاء تغريدة تويتر
        tweet = generator.generate_response(
            "أهمية التعلم المستمر في تطوير المهارات",
            "تويتر",
            "المصرية"
        )
        print("✅ التغريدة الناتجة:\n", tweet)
        
        # إنشاء منشور لينكدإن
        linkedin_post = generator.generate_response(
            "كيفية بناء شبكة علاقات مهنية ناجحة",
            "لينكدإن"
        )
        print("\n✅ منشور لينكدإن:\n", linkedin_post)
        
    except Exception as e:
        print("❌ حدث خطأ:", str(e))
