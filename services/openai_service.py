import re
import logging
import os
import random
from openai import OpenAI
from typing import Optional, Dict

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
        self.client = self._initialize_client()
        self.dialect_guides = {
            "الفصحى المبسطة": "استخدم لغة عربية مبسطة وسهلة الفهم",
            "اليمنية": "استخدم: عادك، شوف، معك خبر؟، شوية، قدك، تمام",
            "الخليجية": "استخدم: بعد، زين، مره، عاد، وايد",
            "المصرية": "استخدم: خلاص، يعني، قوي، جامد، تمام، يلا",
            "الشامية": "استخدم: هلّق، شو القصة، كتير، تمام، بالهداوة",
            "المغربية": "استخدم: واخا، بزاف، دابا، خويا، زعما، مزيان"
        }
        self.emoji_sets = {
            'تويتر': ["🐦", "💬", "🔄", "❤️", "👏"],
            'لينكدإن': ["💼", "📈", "🌐", "🤝", "🏆"],
            'إنستغرام': ["📸", "❤️", "👍", "😍", "🔥"]
        }

    def _initialize_client(self) -> OpenAI:
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            logger.error("OPENROUTER_API_KEY غير موجود في متغيرات البيئة")
            raise ValueError("API key is required")
        
        return OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

    def _clean_content(self, text: str, min_length: int = 20) -> Optional[str]:
        if not text or len(text.strip()) < min_length:
            return None

        try:
            arabic_pattern = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
            symbols_pattern = r'[!؟.,،؛:\-\#@_()\d\s]'
            emoji_pattern = r'[\U0001F300-\U0001F6FF\u2600-\u26FF\u2700-\u27BF]'
            allowed_pattern = f'{arabic_pattern}|{symbols_pattern}|{emoji_pattern}'
            
            cleaned = re.sub(f'[^{allowed_pattern}]', '', text)
            cleaned = re.sub(r'\s+', ' ', cleaned)
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
            return cleaned.strip()
        except Exception as e:
            logger.error(f"فشل تنظيف النص: {e}")
            return None

    def generate_response(
        self,
        user_input: str,
        platform: str,
        dialect: Optional[str] = None,
        max_retries: int = 3
    ) -> str:
        """الدالة الرئيسية التي يتم استيرادها من ملف generate.py"""
        platform_config = {
            "تويتر": {
                "template": "اكتب تغريدة عن: {topic}\n- الطول: 20-280 حرفًا\n- أضف 1-2 إيموجي\n{style}",
                "max_tokens": 280,
                "min_length": 20,
                "temperature": 0.7
            },
            "لينكدإن": {
                "template": "اكتب منشور لينكدإن عن: {topic}\n- الطول: 100-600 كلمة\n- أضف 2-3 إيموجي\n{style}",
                "max_tokens": 600,
                "min_length": 100,
                "temperature": 0.7
            },
            "إنستغرام": {
                "template": "اكتب منشور إنستغرام عن: {topic}\n- الطول: 50-300 حرف\n- أضف 2-3 إيموجي\n{style}",
                "max_tokens": 300,
                "min_length": 50,
                "temperature": 0.8
            }
        }

        if platform not in platform_config:
            return f"المنصة غير مدعومة. الخيارات: {', '.join(platform_config.keys())}"

        config = platform_config[platform]
        style_note = f"\nاستخدم اللهجة {dialect}:\n{self.dialect_guides.get(dialect, '')}" if dialect else ""
        
        for attempt in range(max_retries):
            try:
                system_msg = config["template"].format(
                    topic=user_input,
                    style=style_note
                )
                
                response = self.client.chat.completions.create(
                    extra_headers={
                        "HTTP-Referer": os.getenv('SITE_URL', 'https://default.com'),
                        "X-Title": os.getenv('SITE_NAME', 'Content Generator'),
                    },
                    extra_body={},
                    model="google/gemini-2.0-flash-thinking-exp:free",
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": f"أنشئ منشور {platform} عن: {user_input}"}
                    ],
                    temperature=config["temperature"],
                    max_tokens=config["max_tokens"],
                    timeout=30
                )
                
                content = response.choices[0].message.content
                cleaned = self._clean_content(content, config["min_length"])
                
                if cleaned:
                    # إضافة إيموجي إذا لم يكن موجودًا
                    if not any(emoji in cleaned for emoji in self.emoji_sets[platform]):
                        cleaned = f"{random.choice(self.emoji_sets[platform])} {cleaned}"
                    return cleaned
                
                logger.warning(f"المحاولة {attempt + 1}: الناتج قصير أو غير صالح")
            except Exception as e:
                logger.error(f"المحاولة {attempt + 1} فشلت: {e}")

        return "⚠️ فشل إنشاء المحتوى. يرجى المحاولة لاحقًا"

# إنشاء نسخة وحيدة من الخدمة
openai_service = OpenAIService()

# تصدير الدالة المطلوبة للاستيراد
def generate_response(user_input: str, platform: str, dialect: Optional[str] = None) -> str:
    return openai_service.generate_response(user_input, platform, dialect)
