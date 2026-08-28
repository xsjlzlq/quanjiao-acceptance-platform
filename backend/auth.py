# -*- coding: utf-8 -*-
"""
auth.py  —— 用户认证 & 细粒度权限管理
"""
import hashlib, json, time, os, base64, hmac
from sqlalchemy import text
from database import SessionLocal

SECRET = os.getenv("AUTH_SECRET", "quanjiao_secret_2026")

def _hash_pwd(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()

def _make_token(payload: dict) -> str:
    payload["iat"] = int(time.time())
    payload["exp"] = int(time.time()) + 86400 * 7
    data = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig  = hmac.new(SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()
    return f"{data}.{sig}"

def _verify_token(token: str):
    try:
        data, sig = token.rsplit(".", 1)
        expected = hmac.new(SECRET.encode(), data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(base64.urlsafe_b64decode(data + "=="))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None

SQL_USERS = """
CREATE TABLE IF NOT EXISTS sys_users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(64) UNIQUE NOT NULL,
    password    VARCHAR(128) NOT NULL,
    role        VARCHAR(16) NOT NULL DEFAULT 'user',
    created_at  TIMESTAMP DEFAULT NOW()
);
"""

SQL_PERMS = """
CREATE TABLE IF NOT EXISTS sys_permissions (
    username    VARCHAR(64) PRIMARY KEY,
    perms       JSONB NOT NULL DEFAULT '{}'::jsonb
);
"""

# 细粒度权限默认值（全开）
DEFAULT_PERMS = {
    # 一、任务与抽样
    "tasks_sample": True,
    "tasks_clear": True,
    "tasks_export_att4": True,
    "tasks_export_att5": True,
    # 二、外业核查
    "waiye_check": True,
    "waiye_save": True,
    "waiye_export_att8": True,
    "waiye_export_att9": True,
    # 三、内业核查
    "neiye_view": True,
    "neiye_save": True,
    "neiye_export_att6": True,
    "neiye_export_att7": True,
    # 四、得分评定
    "score_view": True,
    "score_export_att10": True,
    "score_export_att11": True,
    # 五、自查整改
    "rectify_view": True,
    "rectify_export_att12": True,
    "rectify_export_att13": True,
    # 六、系统设置
    "settings_autosave": True,
    "settings_security": True,
    "settings_import": True,
}

async def init_auth_db():
    async with SessionLocal() as s:
        await s.execute(text(SQL_USERS))
        await s.execute(text(SQL_PERMS))
        r = await s.execute(text("SELECT id FROM sys_users WHERE username='admin'"))
        if not r.fetchone():
            await s.execute(text(
                "INSERT INTO sys_users(username,password,role) VALUES('admin',:pw,'admin')"
            ), {"pw": _hash_pwd("admin123")})
            await s.execute(text(
                "INSERT INTO sys_permissions(username,perms) VALUES('admin',:p)"
            ), {"p": json.dumps(DEFAULT_PERMS)})
        await s.commit()

async def login(username: str, password: str):
    async with SessionLocal() as s:
        r = await s.execute(
            text("SELECT id,role FROM sys_users WHERE username=:u AND password=:p"),
            {"u": username, "p": _hash_pwd(password)}
        )
        row = r.fetchone()
        if not row:
            return None, "用户名或密码错误"
        token = _make_token({"sub": username, "role": row[1]})
        return token, None

async def get_user_from_token(token: str):
    return _verify_token(token)

async def get_perms(username: str):
    async with SessionLocal() as s:
        r = await s.execute(
            text("SELECT perms FROM sys_permissions WHERE username=:u"),
            {"u": username}
        )
        row = r.fetchone()
        if row:
            p = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            merged = dict(DEFAULT_PERMS)
            merged.update(p)
            return merged
        return dict(DEFAULT_PERMS)

async def set_perms(username: str, perms: dict):
    async with SessionLocal() as s:
        r = await s.execute(
            text("SELECT username FROM sys_permissions WHERE username=:u"), {"u": username}
        )
        if r.fetchone():
            await s.execute(
                text("UPDATE sys_permissions SET perms=:p WHERE username=:u"),
                {"p": json.dumps(perms), "u": username}
            )
        else:
            await s.execute(
                text("INSERT INTO sys_permissions(username,perms) VALUES(:u,:p)"),
                {"u": username, "p": json.dumps(perms)}
            )
        await s.commit()

async def list_users():
    async with SessionLocal() as s:
        r = await s.execute(text(
            "SELECT username, role, created_at FROM sys_users ORDER BY id"
        ))
        return [{"username": row[0], "role": row[1],
                 "created_at": str(row[2])[:10]} for row in r.fetchall()]

async def create_user(username: str, role: str = "user", password: str = "123456"):
    async with SessionLocal() as s:
        r = await s.execute(text("SELECT id FROM sys_users WHERE username=:u"), {"u": username})
        if r.fetchone():
            return False, "用户名已存在"
        await s.execute(
            text("INSERT INTO sys_users(username,password,role) VALUES(:u,:p,:r)"),
            {"u": username, "p": _hash_pwd(password), "r": role}
        )
        await s.execute(
            text("INSERT INTO sys_permissions(username,perms) VALUES(:u,:p)"),
            {"u": username, "p": json.dumps(DEFAULT_PERMS)}
        )
        await s.commit()
        return True, None

async def delete_user(username: str):
    if username == "admin":
        return False, "不能删除管理员账号"
    async with SessionLocal() as s:
        await s.execute(text("DELETE FROM sys_users WHERE username=:u"), {"u": username})
        await s.execute(text("DELETE FROM sys_permissions WHERE username=:u"), {"u": username})
        await s.commit()
        return True, None

async def reset_password(username: str, new_pwd: str):
    async with SessionLocal() as s:
        await s.execute(
            text("UPDATE sys_users SET password=:p WHERE username=:u"),
            {"p": _hash_pwd(new_pwd), "u": username}
        )
        await s.commit()

async def change_password(username: str, old_pwd: str, new_pwd: str):
    async with SessionLocal() as s:
        r = await s.execute(
            text("SELECT id FROM sys_users WHERE username=:u AND password=:p"),
            {"u": username, "p": _hash_pwd(old_pwd)}
        )
        if not r.fetchone():
            return False, "原密码错误"
        await s.execute(
            text("UPDATE sys_users SET password=:p WHERE username=:u"),
            {"p": _hash_pwd(new_pwd), "u": username}
        )
        await s.commit()
        return True, None