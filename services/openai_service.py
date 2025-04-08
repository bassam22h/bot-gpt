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
    """تنظيف النص مع الحفاظ على الأحرف العربية والترقيم الأساسي"""
    if not text:
        return ""
        
    arabic_pattern = r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]'
    allowed = r'[#@_،؛:؟!ـ.، \n0-9]'
    emojis = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]'
    
    try:
        clean = re.sub(
            fr'[^{arabic_pattern}{allowed}{emojis}]', 
            '', 
            str(text)
        )
        clean = re.sub(r'\n+', '\n', clean)
        clean = re.sub(r'[ ]+', ' ', clean)
        return clean.strip()
    except Exception as e:
        logging.error(f"Error in clean_text: {str(e)}")
        return str(text)[:500]  # إرجاع جزء من النص في حالة الخطأ

async def generate_post(user_input, platform):
    """إنشاء منشور احترافي مع معالجة الأخطاء المحسنة"""
    platform_rules = {
        "تويتر": {
            "length": "180-280 حرفاً",
            "hashtags": "2-3",
            "max_tokens": 300,
            "example": "🌱 نصائح لريادة الأعمال:\n- ابدأ صغيراً فكر كبيراً\n- استثمر في العلاقات\n- تعلم من الأخطاء\nالنجاح رحلة! #ريادة_أعمال #تطوير_ذات"
        },
        "لينكدإن": {
            "length": "300-600 حرفاً",
            "hashtags": "3-5",
            "max_tokens": 500,
            "example": "🚀 استراتيجيات تسويقية ناجحة:\n1. حدد جمهورك بدقة\n2. أنشئ محتوى ذو قيمة\n3. استخدم البيانات\nشاركنا تجربتك! #تسويق #استراتيجيات #نمو"
        },
        "إنستغرام": {
            "length": "220-400 حرفاً",
            "hashtags": "4-5",
            "max_tokens": 400,
            "example": "✨ وصفة كعك سهلة 🍰\n- كوب طحين\n- ملعقة بيكنج باودر\n- نصف كوب سكر\nاخلط المكونات واخبزها\n#وصفات #حلويات #مطبخ"
        }
    }

    if platform not in platform_rules:
        return "⚠️ المنصة غير مدعومة. الرجاء استخدام تويتر، لينكدإن أو إنستغرام."

    system_content = f"""
    أنت كاتب محتوى عربي محترف. اكتب منشوراً لـ {platform} بالعربية فقط وفق:
    - الطول: {platform_rules[platform]['length']}
    - الهيكل:
      * مقدمة جذابة
      * 3 نقاط رئيسية (كل نقطة في سطر)
      * خاتمة
    - استخدم {platform_rules[platform]['hashtags']} هاشتاقات
    - 2-3 إيموجي مناسبة
    
    مثال:
    {platform_rules[platform]['example']}
    
    المطلوب:
    """

    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-v3-base:free",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": str(user_input)[:1000]}  # تقليل طول المدخلات
            ],
            temperature=0.7,
            max_tokens=platform_rules[platform]['max_tokens'],
            timeout=15  # زيادة وقت الانتظار
        )

        if not response or not response.choices:
            raise ValueError("لا يوجد رد من الخادم")

        result = response.choices[0].message.content if hasattr(response.choices[0].message, 'content') else ""

        if not result:
            raise ValueError("الناتج فارغ")

        cleaned_result = clean_text(result)
        
        if len(cleaned_result) < 20:
            raise ValueError("الناتج قصير جداً")

        logging.info(f"تم إنشاء منشور لـ {platform}")
        return cleaned_result

    except Exception as e:
        error_msg = f"عذراً، حدث خطأ: {str(e)}"
        logging.error(f"Error: {error_msg}\nInput: {user_input}\nPlatform: {platform}")
        return f"⚠️ {error_msg}\n\nيمكنك المحاولة مرة أخرى أو تعديل طلبك."
