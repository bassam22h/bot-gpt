FROM python:3.9-slim

WORKDIR /app

# نسخ ملف requirements.txt وتثبيت الحزم
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي الملفات في المشروع إلى داخل الحاوية
COPY . .

# الأمر لتشغيل البوت (main.py)
CMD ["python", "main.py"]
