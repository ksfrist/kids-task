"""
Kids Task - Flask Backend v3
Token 认证 + 激励机制
"""
import sys, os, uuid
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify
from models.database import (
    init_db, create_family, get_family_by_code, create_user, login_user,
    get_user_star_balance, get_user_stickers, get_user_badges,
    get_user_tasks, get_pending_tasks, create_task,
    submit_task, approve_task, get_weekly_stats, get_children,
    BADGE_DEFS, STAR_REWARD_MAP, STICKER_BY_CATEGORY
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "kids-task-dev-secret-2026")

# ─── CORS ─────────────────────────────────────────────
@app.after_request
def cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    return resp

# ─── Token 认证 ────────────────────────────────────────
TOKEN_MAP = {}

def get_user_from_token():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    uid = TOKEN_MAP.get(auth[7:])
    if not uid:
        return None
    from models.database import get_conn
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return dict(row) if row else None

def require_auth(f):
    from functools import wraps
    @wraps(f)
    def deco(*args, **kwargs):
        user = get_user_from_token()
        if not user:
            return jsonify({"code": 401, "error": "请先登录"}), 401
        return f(user, *args, **kwargs)
    return deco

def require_parent(f):
    from functools import wraps
    @wraps(f)
    def deco(user, *args, **kwargs):
        if user["role"] != "parent":
            return jsonify({"code": 403, "error": "需要家长权限"}), 403
        return f(user, *args, **kwargs)
    return deco

def ok(data, **kw):
    r = {"code": 0, "data": data}
    r.update(kw)
    return jsonify(r)

def err(msg, code=400):
    return jsonify({"code": code, "error": msg}), code

# ─── 认证 ──────────────────────────────────────────────
@app.route("/auth/register", methods=["POST"])
def register():
    d = request.get_json() or {}
    username = d.get("username", "").strip()
    password = d.get("password", "")
    nickname = d.get("nickname", username or "家长")
    family_name = d.get("family_name", "我的家")
    if len(username) < 3: return err("用户名至少3位")
    if len(password) < 4: return err("密码至少4位")
    try:
        fam = create_family(family_name)
        user = create_user(username, password, nickname, "parent", fam["id"])
    except ValueError as e:
        return err(str(e))
    token = str(uuid.uuid4()).replace("-", "")
    TOKEN_MAP[token] = user["id"]
    return ok({**{k: user[k] for k in ["id","nickname","role","family_id"]},
               "family_name": fam["name"], "invite_code": fam["invite_code"], "token": token})

@app.route("/auth/login", methods=["POST"])
def login():
    d = request.get_json() or {}
    user = login_user(d.get("username","").strip(), d.get("password",""))
    if not user:
        return err("用户名或密码错误", 401)
    token = str(uuid.uuid4()).replace("-", "")
    TOKEN_MAP[token] = user["id"]
    return ok({**{k: user[k] for k in ["id","nickname","role","family_id"]}, "token": token})

@app.route("/auth/logout", methods=["POST"])
def logout():
    auth = request.headers.get("Authorization","")
    if auth.startswith("Bearer "):
        TOKEN_MAP.pop(auth[7:], None)
    return ok({"msg": "已退出"})

@app.route("/auth/me")
def me():
    user = get_user_from_token()
    if not user:
        return err("未登录", 401)
    return ok({"user_id": user["id"], "role": user["role"], "family_id": user["family_id"], "nickname": user["nickname"]})

# ─── 家庭 ──────────────────────────────────────────────
@app.route("/family/join", methods=["POST"])
@require_auth
@require_parent
def add_child(user):
    d = request.get_json() or {}
    child_name = d.get("child_name","").strip()
    if not child_name: return err("孩子名字不能为空")
    try:
        child = create_user(
            d.get("username","") or f"child_{user['id']}_{uuid.uuid4().hex[:6]}",
            d.get("password","123456"),
            child_name, "child", user["family_id"]
        )
    except ValueError as e:
        return err(str(e))
    return ok({"user_id": child["id"], "nickname": child["nickname"], "username": d.get("username",""), "password": d.get("password","123456")})

@app.route("/family/invite", methods=["GET"])
@require_auth
def get_invite(user):
    from models.database import get_conn
    conn = get_conn()
    row = conn.execute("SELECT invite_code, name FROM families WHERE id=?", (user["family_id"],)).fetchone()
    conn.close()
    return ok({"invite_code": row["invite_code"], "family_name": row["name"]}) if row else err("家庭不存在", 404)

@app.route("/family/join/accept", methods=["POST"])
def accept_invite():
    d = request.get_json() or {}
    code = d.get("invite_code","").strip().upper()
    fam = get_family_by_code(code)
    if not fam: return err("邀请码无效", 404)
    try:
        user = create_user(
            d.get("username","").strip(),
            d.get("password","123456"),
            d.get("nickname",""),
            d.get("role","child"),
            fam["id"]
        )
    except ValueError as e:
        return err(str(e))
    token = str(uuid.uuid4()).replace("-","")
    TOKEN_MAP[token] = user["id"]
    return ok({**{k: user[k] for k in ["id","nickname","role","family_id"]}, "family_name": fam["name"], "token": token})

# ─── 孩子面板 ───────────────────────────────────────────
@app.route("/child/profile")
@require_auth
def child_profile(user):
    bal = get_user_star_balance(user["id"])
    stickers = get_user_stickers(user["id"])
    badges = get_user_badges(user["id"])
    tasks = get_user_tasks(user["id"], user["role"])
    badge_list = []
    for b in badges:
        info = BADGE_DEFS.get(b["badge_key"], (b["badge_key"],"",""))
        badge_list.append({"key": b["badge_key"], "name": info[0], "emoji": info[1]})
    return ok({"balance": bal, "stickers": stickers, "badges": badge_list, "tasks": tasks})

# ─── 任务 ──────────────────────────────────────────────
@app.route("/tasks", methods=["GET"])
@require_auth
def list_tasks(user):
    tasks = get_user_tasks(user["id"], user["role"])
    return ok(tasks)

@app.route("/tasks/pending")
@require_auth
@require_parent
def pending_tasks(user):
    tasks = get_pending_tasks(user["family_id"])
    for t in tasks:
        b = get_user_star_balance(t["assigned_id"])
        t["child_balance"] = b["total"]
    return ok(tasks)

@app.route("/tasks", methods=["POST"])
@require_auth
@require_parent
def new_task(user):
    d = request.get_json() or {}
    title = d.get("title","").strip()
    if not title: return err("任务名称不能为空")
    task = create_task(
        family_id=user["family_id"], creator_id=user["id"],
        title=title, assigned_id=d.get("assigned_id"),
        category=d.get("category","habit"), difficulty=d.get("difficulty",1),
        frequency=d.get("frequency","once"), description=d.get("description",""),
        deadline=d.get("deadline")
    )
    return ok({"task_id": task["id"], "title": task["title"],
                "star_reward": task["star_reward"], "sticker_key": task["sticker_key"]})

@app.route("/tasks/<int:tid>/submit", methods=["POST"])
@require_auth
def do_submit(user, tid):
    submit_task(tid)
    return ok({"status": "submitted", "task_id": tid})

@app.route("/tasks/<int:tid>/approve", methods=["POST"])
@require_auth
@require_parent
def do_approve(user, tid):
    result = approve_task(tid, user["id"])
    if "error" in result: return err(result["error"], 404)
    return ok(result)

@app.route("/tasks/<int:tid>/reject", methods=["POST"])
@require_auth
@require_parent
def do_reject(user, tid):
    from models.database import get_conn
    conn = get_conn()
    conn.execute("UPDATE tasks SET status='rejected' WHERE id=?", (tid,))
    conn.execute("INSERT INTO reviews (task_id,reviewer_id,action,comment) VALUES (?,?,'reject',?)",
                 (tid, user["id"], request.get_json().get("comment","")))
    conn.commit()
    conn.close()
    return ok({"status": "rejected"})

# ─── 奖励 ──────────────────────────────────────────────
@app.route("/rewards/catalog")
def rewards_catalog():
    return ok({
        "star_reward_table": STAR_REWARD_MAP,
        "sticker_themes": STICKER_BY_CATEGORY,
        "badges": [{"key": k, "name": v[0], "emoji": v[1], "desc": v[2]} for k, v in BADGE_DEFS.items()]
    })

@app.route("/rewards/children")
@require_auth
@require_parent
def children_balances(user):
    children = get_children(user["family_id"])
    result = []
    for c in children:
        b = get_user_star_balance(c["id"])
        s = get_user_stickers(c["id"])
        b2 = get_user_badges(c["id"])
        result.append({**c, **b, "sticker_count": len(s), "badge_count": len(b2)})
    return ok(result)

# ─── 统计 ──────────────────────────────────────────────
@app.route("/stats/weekly")
@require_auth
@require_parent
def weekly(user):
    stats = get_weekly_stats(user["family_id"])
    children = get_children(user["family_id"])
    child_stats = []
    for c in children:
        b = get_user_star_balance(c["id"])
        child_stats.append({"id": c["id"], "nickname": c["nickname"], **b})
    return ok({**stats, "children": child_stats})

# ─── 健康检查 ───────────────────────────────────────────
@app.route("/health")
def health():
    from datetime import datetime
    return ok({"status": "ok", "time": datetime.now().isoformat()})

# ─── 启动 ──────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("小星星任务宝 后端启动")
    print("本地访问：http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host="0.0.0.0", port=5000, debug=True)
