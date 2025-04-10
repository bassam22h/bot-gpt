import os
import json
import firebase_admin
from firebase_admin import credentials, db

# تحميل بيانات الاعتماد من المتغير البيئي أو الملف
if not firebase_admin._apps:
    if os.getenv("FIREBASE_CREDENTIALS_JSON"):
        cred_info = json.loads(os.getenv("FIREBASE_CREDENTIALS_JSON"))
        cred = credentials.Certificate(cred_info)
    else:
        cred = credentials.Certificate("firebase-key.json")

    firebase_admin.initialize_app(cred, {
        'databaseURL': os.getenv("FIREBASE_DB_URL")  # مثال: https://your-id.firebaseio.com/
    })

# المسار الأساسي للمستخدمين في قاعدة البيانات
USERS_REF = db.reference("users")

def get_user_count(user_id: int) -> int:
    data = USERS_REF.child(str(user_id)).get()
    return data.get("count", 0) if data else 0

def increment_user_count(user_id: int):
    count = get_user_count(user_id)
    USERS_REF.child(str(user_id)).set({"count": count + 1})

def reset_user_count(user_id: int):
    USERS_REF.child(str(user_id)).set({"count": 0})

def get_all_users():
    return USERS_REF.get() or {}
