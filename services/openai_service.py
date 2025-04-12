import re
import logging
import os
import random
from openai import OpenAI
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

    def _initialize_client(self) -> OpenAI:
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            logger.error("OPENROUTER_API_KEY غير موجود")
            raise ValueError("API key is required")
        return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)

    def _clean_content(self, text: str, min_length: int) -> Tuple[Optional[str], bool]:
        """تنظيف المحتوى مع تقرير إذا كان فارغاً"""
        if not text:
            return None, True
            
        text = re.sub(r'يَا?\s?[اأإآ]?[صش]اح?ب?ي?\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bخو?يَ?ا?\b', '', text, flags=re.IGNORECASE)
        
        arabic_chars = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
        symbols = r'[!؟.,،؛:\-\#@_()\d\s]'
        emojis = r'[\U0001F300-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
        pattern = f'[{arabic_chars}{symbols}{emojis}]'
        
        cleaned = re.sub(f'[^{pattern}]', '', text)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        if len(cleaned) < min_length:
            return None, False
            
        return cleaned, True

    def _generate_safe_content(self, prompt: str, system_msg: str, platform: str) -> Optional[str]:
        """إنشاء محتوى مع معالجة أخطاء شاملة"""
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
                        "content": system_msg + "\n- يجب أن يكون المحتوى كاملاً ومفيداً"
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800 if platform == 'لينكدإن' else 400,
                timeout=60  # زيادة وقت الانتظار
            )
            
            if not response or not response.choices:
                logger.error("الرد من API غير صالح أو فارغ")
                return None
                
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء المحتوى: {str(e)}")
            return None

    def generate_response(self, user_input: str, platform: str, dialect: Optional[str] = None) -> str:
        """الدالة الرئيسية مع ضمانات إضافية"""
        if not user_input or not platform:
            return "⚠️ المدخلات غير صالحة"
            
        if platform not in self.emoji_sets:
            return f"⚠️ المنصة غير مدعومة. الخيارات: {', '.join(self.emoji_sets.keys())}"

        dialect_guides = {
            "اليمنية": "استخدم لهجة يمنية أصيلة بكلمات مثل: عادك، شوف، قدك، تمام، طيب، ابسر، صنديد",
            "المصرية": "استخدم لهجة مصرية بكلمات مثل: خلاص، يعني، قوي، جامد، تمام، يلا، اهو",
            "الشامية": "استخدم لهجة شامية بكلمات مثل: هلّق، شو القصة، كتير، منيح، بالهداوة",
            "المغربية": "استخدم لهجة مغربية بكلمات مثل: واخا، بزاف، دابا، زعما، مزيان",
            "الخليجية": "استخدم لهجة خليجية بكلمات مثل: بعد، زين، مره، عاد، وايد",
            "الفصحى المبسطة": "استخدم لغة عربية فصيحة مبسطة"
        }

        system_msg = f"""أنت كاتب محتوى عربي محترف لـ {platform}. اكتب منشورًا عن:
"{user_input}"

المتطلبات:
1. المحتوى مفصل وغني بالمعلومات
2. استخدم أسلوبًا {dialect_guides.get(dialect, 'احترافيًا')}
3. الطول الأدنى: {self.min_lengths[platform]} حرف
4. أضف {2 if platform == 'تويتر' else 3} إيموجي
5. تجنب مخاطبة القارئ مباشرة"""

        for attempt in range(3):
            try:
                content = self._generate_safe_content(
                    prompt=f"أنشئ منشور {platform} عن: {user_input}",
                    system_msg=system_msg,
                    platform=platform
                )
                
                if not content:
                    continue
                    
                cleaned, is_valid = self._clean_content(content, self.min_lengths[platform])
                
                if is_valid and cleaned:
                    if not any(emoji in cleaned for emoji in self.emoji_sets[platform]):
                        cleaned = f"{random.choice(self.emoji_sets[platform])} {cleaned}"
                    return cleaned
                    
                logger.warning(f"المحاولة {attempt + 1}: المحتوى غير صالح - الطول: {len(content) if content else 0}")
                
            except Exception as e:
                logger.error(f"المحاولة {attempt + 1} فشلت: {str(e)}")

        return "⚠️ فشل إنشاء محتوى يلبي المتطلبات. يرجى تعديل المدخلات والمحاولة مرة أخرى"

# تصدير الدالة
openai_service = OpenAIService()
generate_response = openai_service.generate_response
