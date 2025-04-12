import re
import logging
import os
import random
from openai import OpenAI
from typing import Optional, Dict

logger = logging.getLogger('ArabicContentGenerator')

class OpenAIService:
    def __init__(self):
        self.client = self._initialize_client()
        self.dialect_guides = {
            "الفصحى المبسطة": "استخدم لغة عربية واضحة وسهلة بدون تعقيد",
            "اليمنية": "استخدم: عادك، شوف، معك خبر؟، شوية، قدك، تمام، طيب، ابسر",
            "الخليجية": "استخدم: بعد، زين، مره، عاد، وايد، على طاري، حيل",
            "المصرية": "استخدم: خلاص، يعني، قوي، جامد، تمام، يلا، بص، اهو",
            "الشامية": "استخدم: هلّق، شو القصة، كتير، تمام، بالهداوة، منيح",
            "المغربية": "استخدم: واخا، بزاف، دابا، خويا، زعما، مزيان، هاد"
        }
        self.emoji_sets = {
            'تويتر': ["🐦", "💬", "🔄", "❤️", "👏"],
            'لينكدإن': ["💼", "📈", "🌐", "🤝", "🏆"],
            'إنستغرام': ["📸", "❤️", "👍", "😍", "🔥"]
        }
        self.min_lengths = {
            'تويتر': 50,  # زيادة الحد الأدنى
            'لينكدإن': 150,
            'إنستغرام': 80
        }

    def _initialize_client(self) -> OpenAI:
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    def _ensure_content_quality(self, text: str, platform: str) -> Optional[str]:
        """تحقق من جودة المحتوى وأضف إيموجي إذا لزم"""
        if not text or len(text.strip()) < self.min_lengths[platform]:
            return None

        # تنظيف النص
        arabic_pattern = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
        symbols = r'[!؟.,،؛:\-\#@_()\d\s]'
        emojis = r'[\U0001F300-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
        pattern = f'[{arabic_pattern}{symbols}{emojis}]'
        
        cleaned = re.sub(f'[^{pattern}]', '', text)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        if not any(emoji in cleaned for emoji in self.emoji_sets[platform]):
            cleaned = f"{random.choice(self.emoji_sets[platform])} {cleaned}"
        
        return cleaned if len(cleaned) >= self.min_lengths[platform] else None

    def _generate_with_retry(self, prompt: str, system_msg: str, platform: str, max_retries: int = 3) -> Optional[str]:
        """دالة أساسية مع إعادة المحاولة وتحسين الطلبات"""
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": os.getenv('SITE_URL', 'https://default.com'),
                        "X-Title": os.getenv('SITE_NAME', 'Content Generator'),
                    },
                    extra_body={"length_penalty": 1.5},  # تشجيع النموذج على إنتاج محتوى أطول
                    model="google/gemini-2.0-flash-thinking-exp:free",
                    messages=[
                        {"role": "system", "content": f"{system_msg}\n- يجب أن يكون المحتوى مفصلًا ووافيًا"},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.8,  # زيادة الإبداع قليلاً
                    max_tokens=400 if platform == 'تويتر' else 800,
                    timeout=45
                )
                
                content = response.choices[0].message.content
                if quality_content := self._ensure_content_quality(content, platform):
                    return quality_content
                
                logger.warning(f"المحاولة {attempt+1}: المحتوى قصير - الطول: {len(content)}")
            except Exception as e:
                logger.error(f"المحاولة {attempt+1} فشلت: {str(e)}")
        
        return None

    def generate_response(self, user_input: str, platform: str, dialect: Optional[str] = None) -> str:
        """الدالة الرئيسية المعدلة مع تحسينات الجودة"""
        if platform not in self.emoji_sets:
            return "⚠️ المنصة غير مدعومة. الخيارات: تويتر، لينكدإن، إنستغرام"

        style_note = f"\n\nاستخدم اللهجة {dialect}:\n{self.dialect_guides.get(dialect, '')}" if dialect else ""
        
        system_msg = f"""أنت كاتب محتوى عربي محترف لـ {platform}. اكتب منشورًا عن:
"{user_input}"
{style_note}

المتطلبات:
1. المحتوى مفصل وغني بالمعلومات
2. استخدم لغة طبيعية وسلسة
3. أضف {2 if platform == 'تويتر' else 3} إيموجي
4. تجنب التكرار
5. الطول الأدنى: {self.min_lengths[platform]} حرف"""

        result = self._generate_with_retry(
            prompt=f"أنشئ منشور {platform} عن: {user_input}",
            system_msg=system_msg,
            platform=platform
        )

        return result or "⚠️ تعذر إنشاء محتوى يلبي متطلبات الجودة. يرجى المحاولة مرة أخرى"

# تصدير الدالة
openai_service = OpenAIService()
generate_response = openai_service.generate_response
