"""
Kids Task - Backend Config
数据库配置：SQLite（开发用）→ MySQL（生产用，一行切换
"""
import os

# 数据库 URI
# 开发：SQLite（文件数据库，无需安装，即开即用）
# 生产：MySQL（云数据库，需要 pymysql）
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # "sqlite" | "mysql"

if DB_TYPE == "mysql":
    DB_URI = os.getenv(
        "MYSQL_URI",
        "mysql+pymysql://user:password@localhost:3306/kids_task?charset=utf8mb4"
    )
else:
    # SQLite 路径（项目根目录下的 data/ 目录）
    db_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(db_dir, exist_ok=True)
    DB_URI = f"sqlite:///{os.path.join(db_dir, 'kids_task.db')}"

# Flask 配置
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
DEBUG = os.getenv("FLASK_DEBUG", "1") == "1"

# 微信小程序 AppID/Secret（生产环境从环境变量读取）
WECHAT_APPID = os.getenv("WECHAT_APPID", "")
WECHAT_SECRET = os.getenv("WECHAT_SECRET", "")

# 激励机制配置
STAR_COIN_WEEKLY_LIMIT = 50          # 星星币每周上限
STAR_COIN_DAILY_RESET_DOW = 1         # 周几重置（1=周一）
REWARD_APPLY_COOLDOWN = 3600          # 申请审核冷却时间（秒）
