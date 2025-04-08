import re
import logging
from openai import OpenAI
from config import OPENROUTER_API_KEY

# إعداد نظام تسجيل الأخطاء
logging.basicConfig(
    filename='bot_errors.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

def clean_text(text):
    """
    تنظيف النص من أي أحرف غير مرغوب فيها مع الحفاظ على:
    - الأحرف العربية
    - الأرقام
    - علامات الترقيم العربية
    - الإيموجي المسموح بها
    """
    arabic_pattern = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
    allowed_symbols = r'[#_،؛:؟!ـ.، \n]'
    emojis = r'[☕🌱🏺✨🇾🇪🪔🌾🚀💡🤝]'
    
    clean = re.sub(
        fr'[^{arabic_pattern}{allowed_symbols}{emojis}0-9]', 
        '', 
        text
    )
    
    # تحسين المسافات والفواصل
    clean = re.sub(r'[\s\n]+', '\n', clean).strip()
    clean = re.sub(r'[،]+', '،', clean)
    clean = re.sub(r'[.]+', '.', clean)
    
    return clean

def quality_check(text):
    """
    التحقق من جودة النص الناتج:
    - وجود حد أدنى من الأحرف العربية
    - الهيكل الأساسي للمنشور
    """
    # التحقق من وجود محتوى عربي كافٍ
    arabic_chars = re.findall(r'[\u0600-\u06FF]', text)
    if len(arabic_chars) < 20:
        return False
        
    # التحقق من الهيكل الأساسي (مقدمة، نقاط، خاتمة)
    if not re.search(r'^.*\n.*\n- .*\n- .*\n- .*\n.*$', text):
        return False
        
    return True

async def generate_post(user_input, platform):
    """
    إنشاء منشور احترافي حسب المنصة المحددة
    """
    platform_rules = {
        "تويتر": {
            "length": "180-280 حرفاً",
            "hashtags": "2-3 هاشتاقات",
            "max_tokens": 300
        },
        "لينكدإن": {
            "length": "300-600 حرفاً",
            "hashtags": "3-5 هاشتاقات",
            "max_tokens": 500
        },
        "إنستغرام": {
            "length": "220-400 حرفاً",
            "hashtags": "4-5 هاشتاقات",
            "max_tokens": 400
        },
    }

    system_prompt = (
        f"أنت كاتب محتوى محترف للغة العربية الفصحى فقط. اكتب منشوراً لـ {platform} وفق الشروط التالية:\n"
        f"1. اللغة: العربية الفصحى فقط (ممنوع استخدام أي لغة أخرى)\n"
        f"2. الطول: {platform_rules[platform]['length']}\n"
        f"3. الهيكل:\n"
        f"   - مقدمة جذابة (سطران)\n"
        f"   - 3 نقاط رئيسية (كل نقطة في سطر منفصل)\n"
        f"   - خاتمة تحفيزية (سطر)\n"
        f"4. الإيموجي: استخدم 2-3 إيموجي مناسبة للمحتوى\n"
        f"5. الهاشتاقات: {platform_rules[platform]['hashtags']} ذات صلة (في آخر المنشور)\n"
        f"6. الممنوعات:\n"
        f"   - أي كلمات غير عربية\n"
        f"   - رموز أو أحرف غير معتمدة\n"
        f"   - جمل غير مكتملة\n"
        "\nمثال لمنشور جيد:\n"
        "مرحباً بكم في عالم التسويق الرقمي! 🚀\n"
        "- استراتيجيات مبتكرة لزيادة المبيعات\n"
        "- تحليل البيانات لفهم العملاء\n"
        "- حلول تسويقية مخصصة لاحتياجاتك\n"
        "للاستفسار عن خدماتنا، تواصلوا معنا اليوم! #تسويق_رقمي #زيادة_مبيعات\n"
        "\nالمحتوى المطلوب:\n"
    )

    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-v3-base:free",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.5,
            max_tokens=platform_rules[platform]['max_tokens'],
            stop=["###"]
        )
        result = response.choices[0].message.content
        
        # التحقق من الجودة وإعادة المحاولة إذا لزم الأمر
        if not quality_check(result):
            logging.warning("جودة النص غير كافية، إعادة المحاولة...")
            return await generate_post(user_input, platform)
            
        cleaned_result = clean_text(result)
        
        # تسجيل النجاح في السجل
        logging.info(f"تم إنشاء منشور بنجاح لـ {platform}")
        return cleaned_result
        
    except Exception as e:
        logging.error(f"OpenAI Error: {e}")
        return "❌ حدث خطأ أثناء إنشاء المنشور. يرجى المحاولة مرة أخرى لاحقاً."
