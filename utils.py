import os
import json
import firebase_admin
from firebase_admin import credentials, db
from datetime import datetime, date
from collections import Counter
import logging

# إعداد المسجل (logger)
logger = logging.getLogger(__name__)

# تهيئة Firebase
def initialize_firebase():
    if not firebase_admin._apps:
        try:
            cred = credentials.Certificate(json.loads(os.getenv("FIREBASE_CREDENTIALS_JSON")))
            firebase_admin.initialize_app(cred, {
                'databaseURL': os.getenv("FIREBASE_DB_URL")
            })
        except Exception as e:
            logger.error(f"Firebase initialization failed: {e}")
            raise

initialize_firebase()

# وظائف إدارة المستخدمين
def get_user_data(user_id: int):
    try:
        return db.reference(f"/users/{user_id}").get() or {"count": 0, "date": str(date.today())}
    except Exception as e:
        logger.error(f"Error getting user data: {e}")
        return {"count": 0}

def save_user_data(user_id: int, data: dict):
    try:
        db.reference(f"/users/{user_id}").set(data)
    except Exception as e:
        logger.error(f"Error saving user data: {e}")

def increment_user_count(user_id: int):
    try:
        user_ref = db.reference(f"/users/{user_id}")
        user_ref.update({"count": firebase_admin.db.Increment(1)})
    except Exception as e:
        logger.error(f"Error incrementing count: {e}")

# وظائف السجلات
def log_post(user_id: int, platform: str, content: str):
    try:
        post_ref = db.reference(f"/logs/{user_id}").push()
        post_ref.set({
            "platform": platform,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error logging post: {e}")

def get_all_logs():
    try:
        return db.reference("/logs").get() or {}
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return {}

# وظائف الإحصائيات
def get_platform_usage(limit=5):
    try:
        logs = get_all_logs()
        platforms = []
        
        for user_logs in logs.values():
            if not isinstance(user_logs, dict):
                continue
                
            for post in user_logs.values():
                if isinstance(post, dict) and post.get("platform"):
                    platforms.append(post["platform"])

        if not platforms:
            return []

        return Counter(platforms).most_common(limit)
    except Exception as e:
        logger.error(f"Error getting platform stats: {e}")
        return []

def reset_user_counts():
    try:
        users_ref = db.reference("/users")
        users = users_ref.get() or {}
        
        updates = {f"{uid}/count": 0 for uid in users}
        users_ref.update(updates)
    except Exception as e:
        logger.error(f"Error resetting counts: {e}")
        raise

def clear_all_logs():
    try:
        db.reference("/logs").delete()
    except Exception as e:
        logger.error(f"Error clearing logs: {e}")
        raise

# وظائف أخرى
def get_daily_new_users():
    try:
        users = db.reference("/users").get() or {}
        today = str(date.today())
        return sum(1 for u in users.values() if u.get('date') == today)
    except Exception as e:
        logger.error(f"Error getting new users: {e}")
        return 0
