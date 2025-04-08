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
    تنظيف النص من أي أحرف غير مرغوب فيها
    """
    # السماح بالأحرف العربية، الأرقام، علامات الترقيم الأساسية والإيموجي
    arabic_pattern = r'[\u0600-\u06FF]'
    allowed = r'[#@_،؛:؟!ـ.، \n0-9]'
    emojis = r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF]'
    
    clean = re.sub(
        fr'[^{arabic_pattern}{allowed}{emojis}]', 
        '', 
        text
    )
    
    # تحسين التنسيق
    clean = re.sub(r'\n+', '\n', clean)  # مسافات متعددة
    clean = re.sub(r'[ ]+', ' ', clean)  # أسطر متعددة
    return clean.strip()

async def generate_post(user_input, platform):
    """
    إنشاء منشور احترافي حسب المنصة المحددة
    """
    platform_rules = {
        "تويتر": {
            "length": "180-280 حرفاً",
            "hashtags": "2-3",
            "max_tokens": 300,
            "examples": [
                "🌱 نصائح لريادة الأعمال:\n"
                "- ابدأ صغيراً فكر كبيراً\n"
                "- استثمر في بناء العلاقات\n"
                "- تعلم من الأخطاء\n"
                "النجاح رحلة وليس وجهة! #ريادة_أعمال #تطوير_ذات"
            ]
        },
        "لينكدإن": {
            "length": "300-600 حرفاً",
            "hashtags": "3-5",
            "max_tokens": 500,
            "examples": [
                "🚀 كيف تبني استراتيجية تسويقية ناجحة؟\n\n"
                "1. حدد جمهورك المستهدف بدقة\n"
                "2. أنشئ محتوى ذو قيمة حقيقية\n"
                "3. استخدم البيانات لتحسين أدائك\n\n"
                "شاركنا تجربتك في التعليقات! #تسويق_رقمي #استراتيجيات_تسويقية #نمو_الأعمال"
            ]
        },
        "إنستغرام": {
            "length": "220-400 حرفاً",
            "hashtags": "4-5",
            "max_tokens": 400,
            "examples": [
                "✨ وصفة سهلة لتحضير الكعك 🍰\n\n"
                "- كوب طحين\n"
                "- ملعقة بيكنج باودر\n"
                "- نصف كوب سكر\n"
                "- بيضة واحدة\n\n"
                "اخلط المكونات جيداً واخبزها على 180 درجة\n"
                "#وصفات #حلويات #مطبخ #وصفات_سهلة"
            ]
        }
    }

    # بناء الرسالة النظامية
    system_content = f"""
    أنت مساعد كتابة محتوى عربي احترافي لمواقع التواصل الاجتماعي.
    المطلوب: كتابة منشور لـ {platform} باللغة العربية الفصحى فقط وفق المواصفات التالية:
    
    - الطول: {platform_rules[platform]['length']}
    - الهيكل:
      * مقدمة جذابة (1-2 جملة)
      * 3 نقاط رئيسية (كل نقطة في سطر)
      * خاتمة تحفيزية
    - استخدم {platform_rules[platform]['hashtags']} هاشتاقات في النهاية
    - مسموح باستخدام 2-3 إيموجي مناسبة
    
    أمثلة لمنشورات جيدة:
    {platform_rules[platform]['examples'][0]}
    
    الممنوعات:
    - أي كلمات غير عربية
    - رموز أو أحرف غريبة
    - محتوى غير منظم
    
    المحتوى المطلوب:
    """

    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-v3-base:free",
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_input}
            ],
            temperature=0.7,
            max_tokens=platform_rules[platform]['max_tokens']
        )
        
        result = response.choices[0].message.content
        cleaned_result = clean_text(result)
        
        # تسجيل النجاح
        logging.info(f"تم إنشاء منشور لـ {platform}: {cleaned_result[:50]}...")
        return cleaned_result
        
    except Exception as e:
        logging.error(f"Error in generate_post: {str(e)}")
        return f"⚠️ عذراً، حدث خطأ أثناء إنشاء المنشور. يرجى المحاولة مرة أخرى.\n{str(e)}"
