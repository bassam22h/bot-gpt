FROM python:3.9-slim

WORKDIR /app

# إنشاء مستخدم غير root
RUN useradd -m botuser && \
    chown -R botuser:botuser /app

# نسخ الملفات كـ root ثم تغيير الملكية
COPY --chown=botuser:botuser . .

USER botuser

# تثبيت المتطلبات
RUN pip install --no-cache-dir -r requirements.txt

CMD ["python", "bot.py"]
