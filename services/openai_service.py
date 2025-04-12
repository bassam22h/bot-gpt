import re
import logging
import os
import random
from openai import OpenAI
from typing import Optional

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
            'لينكدإن': 200,  # زيادة الحد الأدنى لمنشورات لينكدإن
            'إنستغرام': 80
        }

    def _initialize_client(self) -> OpenAI:
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    def _clean_content(self, text: str, min_length: int) -> Optional[str]:
        """تنظيف المحتوى مع ضمان الجودة"""
        if not text or len(text.strip()) < min_length:
            return None

        # إزالة العبارات الشخصية مثل "يا صاحبي"
        text = re.sub(r'يَا?\s?[اأإآ]?[صش]اح?ب?ي?\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bخو?يَ?ا?\b', '', text, flags=re.IGNORECASE)
        
        # تنظيف عام
        arabic_chars = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
        symbols = r'[!؟.,،؛:\-\#@_()\d\s]'
        emojis = r'[\U0001F300-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
        pattern = f'[{arabic_chars}{symbols}{emojis}]'
        
        cleaned = re.sub(f'[^{pattern}]', '', text)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned if len(cleaned) >= min_length else None

    def _generate_content(self, prompt: str, system_msg: str, platform: str) -> Optional[str]:
        """إنشاء المحتوى مع تحسينات للجودة"""
        try:
            response = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": os.getenv('SITE_URL', 'https://default.com'),
                    "X-Title": os.getenv('SITE_NAME', 'Content Generator'),
                },
                extra_body={"length_penalty": 1.5},
                model="google/gemini-2.0-flash-thinking-exp:free",
                messages=[
                    {
                        "role": "system", 
                        "content": system_msg + "\n- تجنب مخاطبة القارئ مباشرة بكلمات مثل 'يا صاحبي' أو 'خوي'"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800 if platform == 'لينكدإن' else 400,
                timeout=45
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating content: {e}")
            return None

    def generate_response(self, user_input: str, platform: str, dialect: Optional[str] = None) -> str:
        """الدالة الرئيسية المعدلة"""
        if platform not in self.emoji_sets:
            return "⚠️ المنصة غير مدعومة"

        # تعليمات عامة لكل المنصات
        system_template = """أنت كاتب محتوى محترف لـ {platform}. اكتب منشورًا عن:
"{topic}"

المتطلبات العامة:
1. استخدم أسلوبًا احترافيًا راقيًا
2. لا تخاطب القارئ مباشرة (تجنب "يا صاحبي" أو "خوي")
3. المحتوى مفصل وغني بالمعلومات
4. استخدم {emoji_count} إيموجي بشكل مناسب
5. الطول الأدنى: {min_length} حرف"""

        # تعليمات خاصة باللهجات
        dialect_instructions = {
            "اليمنية": "استخدم لهجة يمنية راقية دون مخاطبة مباشرة للقارئ. الكلمات المميزة: عادك، شوف، قدك، تمام، طيب، ابسر، صنديد، مواقف رجولية",
            "المصرية": "استخدم لهجة مصرية راقية. الكلمات المميزة: خلاص، يعني، قوي، جامد، تمام، يلا، اهو، كده",
            "الشامية": "استخدم لهجة شامية راقية. الكلمات المميزة: هلّق، شو القصة، كتير، منيح، بالهداوة",
            "المغربية": "استخدم لهجة مغربية راقية. الكلمات المميزة: واخا، بزاف، دابا، زعما، مزيان، هاد",
            "الخليجية": "استخدم لهجة خليجية راقية. الكلمات المميزة: بعد، زين، مره، عاد، وايد، على طاري",
            "الفصحى المبسطة": "استخدم لغة عربية فصيحة مبسطة وسهلة الفهم"
        }

        system_msg = system_template.format(
            platform=platform,
            topic=user_input,
            emoji_count=2 if platform == 'تويتر' else 3,
            min_length=self.min_lengths[platform]
        )

        if dialect and dialect in dialect_instructions:
            system_msg += f"\n\nمتطلبات اللهجة:\n{dialect_instructions[dialect]}"

        for attempt in range(3):
            content = self._generate_content(
                prompt=f"أنشئ منشور {platform} عن: {user_input}",
                system_msg=system_msg,
                platform=platform
            )

            cleaned = self._clean_content(content, self.min_lengths[platform])
            if cleaned:
                # إضافة إيموجي إذا لم يكن موجودًا
                if not any(emoji in cleaned for emoji in self.emoji_sets[platform]):
                    cleaned = f"{random.choice(self.emoji_sets[platform])} {cleaned}"
                return cleaned

            logger.warning(f"المحاولة {attempt + 1}: المحتوى قصير أو غير صالح")

        return "⚠️ تعذر إنشاء محتوى يلبي متطلبات الجودة. يرجى المحاولة مرة أخرى"

# تصدير الدالة
openai_service = OpenAIService()
generate_response = openai_service.generate_response
