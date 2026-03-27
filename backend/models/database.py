"""
Kids Task - Database Models v2
用户名密码登录 + 激励机制
"""
import sqlite3
import os
import uuid
import hashlib
import secrets
from dataclasses import dataclass, field
from typing import Optional, List

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "kids_task.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    # 家庭表
    c.execute("""CREATE TABLE IF NOT EXISTS families (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        invite_code TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )""")

    # 用户表（含密码hash）
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        nickname TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('parent','child')),
        avatar TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (family_id) REFERENCES families(id)
    )""")

    # 任务表
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER NOT NULL,
        creator_id INTEGER NOT NULL,
        assigned_id INTEGER,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        category TEXT DEFAULT 'habit',
        difficulty INTEGER DEFAULT 1 CHECK(difficulty BETWEEN 1 AND 5),
        frequency TEXT DEFAULT 'once' CHECK(frequency IN ('once','daily','weekly')),
        star_reward INTEGER DEFAULT 3,
        sticker_key TEXT DEFAULT '',
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending','submitted','approved','rejected')),
        deadline TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (family_id) REFERENCES families(id),
        FOREIGN KEY (creator_id) REFERENCES users(id),
        FOREIGN KEY (assigned_id) REFERENCES users(id)
    )""")

    # 星星币流水
    c.execute("""CREATE TABLE IF NOT EXISTS star_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        amount INTEGER NOT NULL,
        source TEXT NOT NULL,
        task_id INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (task_id) REFERENCES tasks(id)
    )""")

    # 贴纸收集
    c.execute("""CREATE TABLE IF NOT EXISTS stickers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        sticker_key TEXT NOT NULL,
        task_id INTEGER,
        earned_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (task_id) REFERENCES tasks(id)
    )""")

    # 徽章
    c.execute("""CREATE TABLE IF NOT EXISTS badges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        badge_key TEXT NOT NULL,
        earned_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(user_id, badge_key),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    # 审核记录
    c.execute("""CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER NOT NULL,
        reviewer_id INTEGER NOT NULL,
        action TEXT NOT NULL CHECK(action IN ('approve','reject')),
        comment TEXT DEFAULT '',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (task_id) REFERENCES tasks(id),
        FOREIGN KEY (reviewer_id) REFERENCES users(id)
    )""")

    # 积分兑换
    c.execute("""CREATE TABLE IF NOT EXISTS redemptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        reward_name TEXT NOT NULL,
        star_cost INTEGER NOT NULL,
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected')),
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    # 计划任务（每日/每周自动生成）
    c.execute("""CREATE TABLE IF NOT EXISTS task_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        family_id INTEGER NOT NULL,
        creator_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        category TEXT DEFAULT 'habit',
        difficulty INTEGER DEFAULT 1,
        star_reward INTEGER DEFAULT 3,
        sticker_key TEXT DEFAULT '',
        frequency TEXT DEFAULT 'daily',
        assigned_id INTEGER,
        FOREIGN KEY (family_id) REFERENCES families(id),
        FOREIGN KEY (creator_id) REFERENCES users(id),
        FOREIGN KEY (assigned_id) REFERENCES users(id)
    )""")

    # 数据版本
    c.execute("""CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL DEFAULT (datetime('now')),
        description TEXT DEFAULT ''
    )""")

    conn.commit()
    conn.close()
    print(f"[DB] Initialized at {DB_PATH}")


# ─────────────────────────────────────────
# 密码工具
# ─────────────────────────────────────────
def hash_password(password: str, salt: str = None) -> tuple:
    salt = salt or secrets.token_hex(8)
    h = hashlib.sha256((password + salt).encode()).hexdigest()
    return h, salt

def verify_password(password: str, password_hash: str, salt: str) -> bool:
    h, _ = hash_password(password, salt)
    return h == password_hash


# ─────────────────────────────────────────
# 激励机制常量
# ─────────────────────────────────────────
STAR_REWARD_MAP = {1: 3, 2: 5, 3: 8, 4: 12, 5: 18}   # 难度 → 星星币
STICKER_BY_CATEGORY = {
    "habit":    ["star_green", "star_yellow", "star_red"],
    "study":    ["book_blue", "book_purple", "pencil_gold"],
    "housework":["broom", "plate", "bed"],
    "creative": ["paintbrush", "music_note", "camera"],
}
BADGE_DEFS = {
    "first_task":    ("初出茅庐",    "🌱", "完成第一个任务"),
    "task_10":       ("小有成就",    "🌟", "累计完成10个任务"),
    "task_50":       ("任务达人",    "🏆", "累计完成50个任务"),
    "streak_7":      ("坚持一周",    "🏅", "连续7天完成每日任务"),
    "streak_30":     ("坚持一个月",  "🎖️", "连续30天完成每日任务"),
    "star_100":      ("星星收藏家",  "⭐", "累计获得100星星币"),
    "star_500":      ("星星大王",    "💫", "累计获得500星星币"),
    "sticker_10":    ("贴纸新手",    "🎨", "收集10张贴纸"),
    "sticker_50":    ("贴纸达人",    "🖼️", "收集50张贴纸"),
}


# ─────────────────────────────────────────
# Data Access
# ─────────────────────────────────────────
def create_family(name: str) -> dict:
    code = uuid.uuid4().hex[:8].upper()
    conn = get_conn()
    conn.execute("INSERT INTO families (name, invite_code) VALUES (?, ?)", (name, code))
    conn.commit()
    row = conn.execute("SELECT * FROM families WHERE invite_code=?", (code,)).fetchone()
    conn.close()
    return dict(row)

def get_family_by_code(code: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM families WHERE invite_code=?", (code.upper(),)).fetchone()
    conn.close()
    return dict(row) if row else None

def create_user(username: str, password: str, nickname: str, role: str, family_id: int = None) -> dict:
    pwd_hash, salt = hash_password(password)
    conn = get_conn()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, salt, nickname, role, family_id) VALUES (?, ?, ?, ?, ?, ?)",
            (username, pwd_hash, salt, nickname, role, family_id)
        )
        conn.commit()
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("用户名已存在")
    conn.close()
    return dict(row)

def login_user(username: str, password: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not row:
        conn.close()
        return None
    user = dict(row)
    if not verify_password(password, user["password_hash"], user.get("salt", "")):
        conn.close()
        return None
    conn.close()
    return user

def get_user_star_balance(user_id: int) -> dict:
    conn = get_conn()
    total = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM star_ledger WHERE user_id=?", (user_id,)
    ).fetchone()[0]
    this_week = conn.execute(
        """SELECT COALESCE(SUM(amount),0) FROM star_ledger
           WHERE user_id=? AND created_at >= date('now','-7 days')""", (user_id,)
    ).fetchone()[0]
    conn.close()
    return {"total": total, "this_week": this_week}

def get_user_stickers(user_id: int) -> List[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT sticker_key, earned_at FROM stickers WHERE user_id=? ORDER BY earned_at DESC LIMIT 100",
        (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_badges(user_id: int) -> List[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT badge_key, earned_at FROM badges WHERE user_id=?", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_tasks(user_id: int, role: str) -> List[dict]:
    conn = get_conn()
    if role == "parent":
        rows = conn.execute(
            """SELECT t.*, u.nickname as assigned_name
               FROM tasks t LEFT JOIN users u ON t.assigned_id=u.id
               WHERE t.family_id=(SELECT family_id FROM users WHERE id=?)
               ORDER BY t.created_at DESC LIMIT 50""", (user_id,)
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM tasks
               WHERE assigned_id=? AND status IN ('pending','submitted')
               ORDER BY created_at DESC""", (user_id,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_pending_tasks(family_id: int) -> List[dict]:
    conn = get_conn()
    rows = conn.execute(
        """SELECT t.*, u.nickname as child_name
           FROM tasks t LEFT JOIN users u ON t.assigned_id=u.id
           WHERE t.family_id=? AND t.status='submitted'
           ORDER BY t.created_at ASC""", (family_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def create_task(family_id: int, creator_id: int, title: str, assigned_id: int = None,
                category: str = "habit", difficulty: int = 1, frequency: str = "once",
                description: str = "", deadline: str = None) -> dict:
    star_reward = STAR_REWARD_MAP.get(difficulty, 3)
    import random
    sticker_key = random.choice(STICKER_BY_CATEGORY.get(category, ["star_green"]))

    conn = get_conn()
    conn.execute("""INSERT INTO tasks
        (family_id, creator_id, assigned_id, title, description, category,
         difficulty, frequency, star_reward, sticker_key, deadline)
        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (family_id, creator_id, assigned_id, title, description, category,
         difficulty, frequency, star_reward, sticker_key, deadline))
    conn.commit()
    row = conn.execute("SELECT * FROM tasks WHERE id=last_insert_rowid()").fetchone()
    conn.close()
    return dict(row)

def submit_task(task_id: int) -> None:
    conn = get_conn()
    conn.execute("UPDATE tasks SET status='submitted' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

def approve_task(task_id: int, reviewer_id: int) -> dict:
    """审核通过：发奖励 + 判定徽章"""
    conn = get_conn()
    task = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not task:
        conn.close()
        return {"error": "任务不存在"}

    uid = task["assigned_id"]
    stars = task["star_reward"]
    sticker = task["sticker_key"]

    # 发星星币
    if stars > 0:
        conn.execute(
            "INSERT INTO star_ledger (user_id, amount, source, task_id) VALUES (?, ?, 'task', ?)",
            (uid, stars, task_id)
        )

    # 发贴纸
    if sticker:
        conn.execute(
            "INSERT INTO stickers (user_id, sticker_key, task_id) VALUES (?, ?, ?)",
            (uid, sticker, task_id)
        )

    conn.execute("UPDATE tasks SET status='approved' WHERE id=?", (task_id,))
    conn.execute("INSERT INTO reviews (task_id, reviewer_id, action) VALUES (?,?,'approve')",
                 (task_id, reviewer_id))
    conn.commit()

    # 判定徽章
    new_badges = check_and_award_badges(uid, conn)
    conn.close()

    return {"stars_earned": stars, "sticker": sticker, "new_badges": new_badges}

def check_and_award_badges(user_id: int, conn=None) -> List[dict]:
    """检查徽章条件，返回新增徽章列表"""
    should_close = conn is None
    if conn is None:
        conn = get_conn()

    earned_keys = {r["badge_key"] for r in conn.execute(
        "SELECT badge_key FROM badges WHERE user_id=?", (user_id,)).fetchall()}
    new_badges = []

    # 查统计数据
    total_tasks = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE assigned_id=? AND status='approved'", (user_id,)
    ).fetchone()[0]
    total_stars = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM star_ledger WHERE user_id=?", (user_id,)
    ).fetchone()[0]
    total_stickers = conn.execute(
        "SELECT COUNT(*) FROM stickers WHERE user_id=?", (user_id,)
    ).fetchone()[0]

    # 检查各徽章条件
    checks = [
        ("first_task",   total_tasks >= 1),
        ("task_10",      total_tasks >= 10),
        ("task_50",      total_tasks >= 50),
        ("star_100",     total_stars >= 100),
        ("star_500",     total_stars >= 500),
        ("sticker_10",   total_stickers >= 10),
        ("sticker_50",   total_stickers >= 50),
    ]

    for key, cond in checks:
        if cond and key not in earned_keys:
            conn.execute(
                "INSERT OR IGNORE INTO badges (user_id, badge_key) VALUES (?, ?)",
                (user_id, key)
            )
            new_badges.append({"key": key, "name": BADGE_DEFS[key][0], "emoji": BADGE_DEFS[key][1]})

    if new_badges:
        conn.commit()
    if should_close:
        conn.close()
    return new_badges

def get_weekly_stats(family_id: int) -> dict:
    conn = get_conn()
    completed = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE family_id=? AND status='approved' AND created_at >= date('now','-7 days')",
        (family_id,)
    ).fetchone()[0]
    coins = conn.execute(
        """SELECT COALESCE(SUM(s.amount),0) FROM star_ledger s
           JOIN users u ON s.user_id=u.id WHERE u.family_id=? AND s.created_at >= date('now','-7 days')""",
        (family_id,)
    ).fetchone()[0]
    pending = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE family_id=? AND status='submitted'", (family_id,)
    ).fetchone()[0]
    conn.close()
    return {"completed": completed, "coins_this_week": coins, "pending_review": pending}

def get_children(family_id: int) -> List[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, nickname, avatar FROM users WHERE family_id=? AND role='child'", (family_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# 自动初始化（Flask import 时也执行）
init_db()

if __name__ == "__main__":
    init_db()
