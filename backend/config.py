"""
Kids Task - Backend Config
"""
import os

DB_TYPE = os.getenv("DB_TYPE", "sqlite")
if DB_TYPE == "mysql":
    DB_URI = os.getenv("MYSQL_URI", "mysql+pymysql://...")
else:
    db_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(db_dir, exist_ok=True)
    DB_URI = f"sqlite:///{os.path.join(db_dir, 'kids_task.db')}"

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-2026")
WECHAT_APPID = os.getenv("WECHAT_APPID", "")
WECHAT_SECRET = os.getenv("WECHAT_SECRET", "")
STAR_COIN_WEEKLY_LIMIT = 50
