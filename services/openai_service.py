import re
import logging
from openai import OpenAI
from config import OPENROUTER_API_KEY

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def clean_text(text):
    clean = re.sub(r'[^\w\s#_،؛:؟!ـء-ي٠-٩☕🌱🏺✨🇾🇪🪔🌾🚀💡🤝]', '', text)
    clean = re.sub(r'\n+', '\n', clean).strip()
    return clean

async def generate_post(user_input, platform):
    platform_rules = {
        "تويتر": {"length": "180-280 حرفاً", "hashtags": "2-3 هاشتاقات"},
        "لينكدإن": {"length": "300-600 حرفاً", "hashtags": "3-5 هاشتاقات"},
        "إنستغرام": {"length": "220-400 حرفاً", "hashtags": "4-5 هاشتاقات"},
    }

    system_prompt = f"""أنت كاتب محتوى محترف لمنصة {platform}. استخدم اللغة العربية فقط.
1. طول المنشور: {platform_rules[platform]["length"]}
2. استخدم 3-5 إيموجي مناسبة
3. قسّم المنشور إلى مقدمة، نقاط رئيسية، وخاتمة
4. أضف {platform_rules[platform]["hashtags"]} في النهاية"""

    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-v3-base:free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.5,
            max_tokens=1000
        )
        result = response.choices[0].message.content
        return clean_text(result)
    except Exception as e:
        logging.error(f"OpenAI Error: {e}")
        return "❌ حدث خطأ أثناء إنشاء المنشور."
