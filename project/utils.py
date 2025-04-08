import json
from datetime import datetime

USERS_FILE = "data/users.json"

def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def get_user_limit_status(user_id):
    users = load_users()
    today = str(datetime.utcnow().date())

    if str(user_id) not in users:
        users[str(user_id)] = {"date": today, "count": 0}
        save_users(users)
        return True

    user_data = users[str(user_id)]
    if user_data["date"] != today:
        users[str(user_id)] = {"date": today, "count": 0}
        save_users(users)
        return True

    return user_data["count"] < 5

def increment_user_count(user_id):
    users = load_users()
    today = str(datetime.utcnow().date())

    if str(user_id) not in users or users[str(user_id)]["date"] != today:
        users[str(user_id)] = {"date": today, "count": 1}
    else:
        users[str(user_id)]["count"] += 1

    save_users(users)

def get_total_users():
    users = load_users()
    return len(users)
