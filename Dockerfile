FROM python:3.9-slim

# تعيين دليل العمل
WORKDIR /app

# نسخ requirements.txt إلى الحاوية
COPY requirements.txt .

# تثبيت المتطلبات
RUN pip install --no-cache-dir -r requirements.txt

# نسخ كل الملفات الأخرى
COPY . .

# تشغيل البوت
CMD ["python", "main.py"]
