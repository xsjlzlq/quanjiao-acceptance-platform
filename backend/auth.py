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

async def verify_token_active(token: str):
    """
    深度核验 Token：不仅校验 HMAC 签名与有效期，还校验密码特征码（pwd_ver）。
    若用户修改了密码，旧 Token 中的 pwd_ver 与数据库不一致，直接判定失效，强制下线。
    同时支持按用户绑定的 target_db 定位数据库核验。
    """
    payload = _verify_token(token)
    if not payload:
        return None
    username = payload.get("sub")
    token_pwd_ver = payload.get("pwd_ver")
    user_db = payload.get("target_db")
    if not username:
        return None
    
    async with SessionLocal(db_name=user_db) as s:
        try:
            r = await s.execute(
                text("SELECT password, role, target_db FROM sys_users WHERE username=:u"),
                {"u": username}
            )
            row = r.fetchone()
            if not row:
                return None
            curr_pwd_hash, curr_role, curr_target_db = row[0], row[1], row[2]
            curr_pwd_ver = curr_pwd_hash[:10]
            if token_pwd_ver and token_pwd_ver != curr_pwd_ver:
                return None
            payload["role"] = curr_role
            if curr_target_db:
                payload["target_db"] = curr_target_db
            return payload
        except Exception:
            return None

SQL_USERS = """
CREATE TABLE IF NOT EXISTS sys_users (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(64) UNIQUE NOT NULL,
    password    VARCHAR(128) NOT NULL,
    role        VARCHAR(16) NOT NULL DEFAULT 'user',
    target_db   VARCHAR(64) DEFAULT '',
    created_at  TIMESTAMP DEFAULT NOW()
);
"""

SQL_PERMS = """
CREATE TABLE IF NOT EXISTS sys_permissions (
    username    VARCHAR(64) PRIMARY KEY REFERENCES sys_users(username) ON DELETE CASCADE ON UPDATE CASCADE,
    perms       JSONB NOT NULL DEFAULT '{}'::jsonb
);
"""

# 细粒度权限默认值（普通用户初始模板）
DEFAULT_PERMS = {
    # 一、任务与抽样
    "tasks_dashboard": True,
    "tasks_sample": False,
    "tasks_delete_contractor": False,
    "tasks_clear": False,
    "tasks_export_att4": True,
    "tasks_export_att5": True,
    # 二、外业核查
    "waiye_check": True,
    "waiye_save": True,
    "waiye_export_att8": True,
    "waiye_export_att9": True,
    "waiye_inquiry": True,
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
    # 附件一键导出
    "batch_export": False,
    # 六、系统设置
    "settings_security": True,
    "settings_import": False,
    # 七、使用帮助
    "help_manual": True,
    "help_audit_log": False,
}

# 全量权限字典（管理员 100% 全部权限，全部开启）
ALL_PERMS_DICT = {k: True for k in DEFAULT_PERMS}

async def ensure_user_table_schema(session):
    """
    自愈检测并安全补齐 sys_users 表结构，为 sys_users(username) 建立唯一约束，
    清理孤儿权限残留，并建立 ON DELETE CASCADE 外键级联约束。
    兼容 PostgreSQL 9.5+ 语法。
    """
    try:
        # 1. 补齐 target_db 字段
        r_col = await session.execute(text("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'sys_users' AND column_name = 'target_db'
        """))
        if not r_col.fetchone():
            await session.execute(text("ALTER TABLE sys_users ADD COLUMN target_db VARCHAR(64) DEFAULT '';"))

        # 2. 确保 sys_users(username) 具备唯一约束 (以支持外键引用)
        r_uq = await session.execute(text("""
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_sys_users_username';
        """))
        if not r_uq.fetchone():
            try:
                await session.execute(text("ALTER TABLE sys_users ADD CONSTRAINT uq_sys_users_username UNIQUE (username);"))
            except Exception:
                pass

        # 3. 自动清理 sys_permissions 中已被删除的孤儿账号残留
        await session.execute(text("""
            DELETE FROM sys_permissions 
            WHERE username NOT IN (SELECT username FROM sys_users);
        """))

        # 4. 建立数据库级外键级联约束 (ON DELETE CASCADE)，确保只要 sys_users 被删，sys_permissions 物理级联秒删
        r_fk = await session.execute(text("""
            SELECT 1 FROM pg_constraint WHERE conname = 'fk_sys_permissions_username';
        """))
        if not r_fk.fetchone():
            await session.execute(text("""
                ALTER TABLE sys_permissions 
                ADD CONSTRAINT fk_sys_permissions_username 
                FOREIGN KEY (username) REFERENCES sys_users(username) 
                ON DELETE CASCADE 
                ON UPDATE CASCADE;
            """))
        await session.commit()
    except Exception as e:
        print(f"ensure_user_table_schema notice: {e}")

async def init_auth_db():
    async with SessionLocal() as s:
        await s.execute(text(SQL_USERS))
        await s.execute(text(SQL_PERMS))
        await ensure_user_table_schema(s)
        r = await s.execute(text("SELECT id FROM sys_users WHERE username='admin'"))
        if not r.fetchone():
            await s.execute(text(
                "INSERT INTO sys_users(username,password,role,target_db) VALUES('admin',:pw,'admin','')"
            ), {"pw": _hash_pwd("admin123")})
            await s.execute(text(
                "INSERT INTO sys_permissions(username,perms) VALUES('admin',:p)"
            ), {"p": json.dumps(DEFAULT_PERMS)})
        await s.commit()

async def login(username: str, password: str):
    """
    智能多库登录：
    1. 优先在当前默认库查找；
    2. 若未找到，自动检索其他可用数据库中的 sys_users；
    3. 管理员账号免锁库（随切随走），普通用户签发绑定专属数据库的 Token！
    """
    from database import load_config, list_available_databases
    pwd_hash = _hash_pwd(password)
    cfg = load_config()
    default_db = cfg.get("db_name", "quanjiao")
    
    # 候选数据库查找列表：当前默认库优先，其次其他可用库
    all_dbs = list_available_databases()
    ordered_dbs = [default_db] + [db for db in all_dbs if db != default_db]
    
    for db_candidate in ordered_dbs:
        try:
            async with SessionLocal(db_name=db_candidate) as s:
                await ensure_user_table_schema(s)
                r = await s.execute(
                    text("SELECT id, role, password, COALESCE(target_db, '') FROM sys_users WHERE username=:u AND password=:p"),
                    {"u": username, "p": pwd_hash}
                )
                row = r.fetchone()
                if row:
                    user_role = row[1]
                    # 管理员无需分配特定数据库，target_db 为空，随当前系统全局切换
                    if user_role == "admin" or username == "admin":
                        user_target_db = ""
                    else:
                        user_target_db = row[3].strip() if row[3] else db_candidate
                        
                    pwd_ver = row[2][:10] if row[2] else ""
                    token = _make_token({
                        "sub": username, 
                        "role": user_role, 
                        "pwd_ver": pwd_ver,
                        "target_db": user_target_db
                    })
                    return token, None, (user_target_db or db_candidate)
        except Exception:
            continue
            
    return None, "用户名或密码错误", None

async def get_user_from_token(token: str):
    return _verify_token(token)

async def get_perms(username: str):
    # 管理员角色/admin账号天然拥有全系统 100% 全部权限，任何权限键都恒为 True！
    if username == "admin":
        return dict(ALL_PERMS_DICT)

    async with SessionLocal() as s:
        # 查询用户角色判定是否为 admin
        r_role = await s.execute(
            text("SELECT role FROM sys_users WHERE username=:u LIMIT 1"),
            {"u": username}
        )
        role_row = r_role.fetchone()
        if role_row and role_row[0] == "admin":
            return dict(ALL_PERMS_DICT)

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
    from database import current_db_ctx, load_config
    cur_active_db = current_db_ctx.get() or load_config().get("db_name", "quanjiao")
    async with SessionLocal() as s:
        await ensure_user_table_schema(s)
        try:
            r = await s.execute(text(
                "SELECT username, role, created_at, COALESCE(target_db, '') FROM sys_users ORDER BY id"
            ))
            return [{"username": row[0], "role": row[1],
                     "created_at": str(row[2])[:10],
                     "target_db": row[3] if row[3] else (cur_active_db if row[1] != 'admin' else "")} for row in r.fetchall()]
        except Exception as err:
            print(f"list_users fallback error: {err}")
            # 二次自愈降级
            r2 = await s.execute(text("SELECT username, role, created_at FROM sys_users ORDER BY id"))
            return [{"username": row[0], "role": row[1],
                     "created_at": str(row[2])[:10],
                     "target_db": cur_active_db if row[1] != 'admin' else ""} for row in r2.fetchall()]

async def create_user(username: str, role: str = "user", password: str = "123456", target_db: str = ""):
    from database import current_db_ctx, load_config
    resolved_db = (target_db or current_db_ctx.get() or load_config().get("db_name", "quanjiao")).strip()
    async with SessionLocal() as s:
        await ensure_user_table_schema(s)
        r = await s.execute(text("SELECT id FROM sys_users WHERE username=:u"), {"u": username})
        if r.fetchone():
            return False, "用户名已存在"
        await s.execute(
            text("INSERT INTO sys_users(username,password,role,target_db) VALUES(:u,:p,:r,:td)"),
            {"u": username, "p": _hash_pwd(password), "r": role, "td": resolved_db}
        )
        await s.execute(
            text("""
                INSERT INTO sys_permissions(username, perms) VALUES(:u, :p)
                ON CONFLICT (username) DO UPDATE SET perms = EXCLUDED.perms
            """),
            {"u": username, "p": json.dumps(DEFAULT_PERMS)}
        )
        await s.commit()
        return True, None

async def set_user_target_db(username: str, target_db: str):
    """为账号分配专属目标数据库"""
    async with SessionLocal() as s:
        await ensure_user_table_schema(s)
        await s.execute(
            text("UPDATE sys_users SET target_db=:td WHERE username=:u"),
            {"td": target_db.strip(), "u": username}
        )
        await s.commit()
        return True

async def delete_user(username: str):
    """
    删除账号：
    双重保险删除：先清理从表 sys_permissions，再清理主表 sys_users，
    配合底层数据库的 ON DELETE CASCADE 级联约束，保证 100% 绝对不产生任何孤儿权限数据！
    """
    clean_u = (username or "").strip()
    if clean_u == "admin":
        return False, "不能删除管理员账号"
    async with SessionLocal() as s:
        await ensure_user_table_schema(s)
        # 显式清理从表
        await s.execute(text("DELETE FROM sys_permissions WHERE username=:u"), {"u": clean_u})
        # 显式清理主表
        r = await s.execute(text("DELETE FROM sys_users WHERE username=:u"), {"u": clean_u})
        await s.commit()
        if r.rowcount == 0:
            return False, "未找到该用户账号"
        return True, None

async def reset_password(username: str, new_pwd: str):
    """
    重置密码：
    若重置的是管理员账号，自动在所有可用业务库中同步更新 admin 的密码！
    """
    new_pwd_hash = _hash_pwd(new_pwd)
    is_admin = False
    
    async with SessionLocal() as s:
        await ensure_user_table_schema(s)
        r = await s.execute(text("SELECT role FROM sys_users WHERE username=:u"), {"u": username})
        row = r.fetchone()
        if username == "admin" or (row and row[0] == "admin"):
            is_admin = True
        await s.execute(
            text("UPDATE sys_users SET password=:p WHERE username=:u"),
            {"p": new_pwd_hash, "u": username}
        )
        await s.commit()

    # 管理员多库密码同步
    if is_admin:
        from database import list_available_databases
        for db in list_available_databases():
            try:
                async with SessionLocal(db_name=db) as s_other:
                    await ensure_user_table_schema(s_other)
                    await s_other.execute(
                        text("UPDATE sys_users SET password=:p WHERE username=:u OR (role='admin' AND :u='admin')"),
                        {"p": new_pwd_hash, "u": username}
                    )
                    await s_other.commit()
            except Exception:
                pass

async def change_password(username: str, old_pwd: str, new_pwd: str):
    """
    修改密码：
    若修改的是管理员账号，自动在所有可用业务库中同步更新 admin 的密码，保持全库一致！
    """
    old_pwd_hash = _hash_pwd(old_pwd)
    new_pwd_hash = _hash_pwd(new_pwd)
    is_admin = False

    async with SessionLocal() as s:
        await ensure_user_table_schema(s)
        r = await s.execute(
            text("SELECT id, role FROM sys_users WHERE username=:u AND password=:p"),
            {"u": username, "p": old_pwd_hash}
        )
        row = r.fetchone()
        if not row:
            return False, "原密码错误"
        if username == "admin" or row[1] == "admin":
            is_admin = True
        await s.execute(
            text("UPDATE sys_users SET password=:p WHERE username=:u"),
            {"p": new_pwd_hash, "u": username}
        )
        await s.commit()

    # 管理员多库密码同步
    if is_admin:
        from database import list_available_databases
        for db in list_available_databases():
            try:
                async with SessionLocal(db_name=db) as s_other:
                    await ensure_user_table_schema(s_other)
                    await s_other.execute(
                        text("UPDATE sys_users SET password=:p WHERE username=:u OR (role='admin' AND :u='admin')"),
                        {"p": new_pwd_hash, "u": username}
                    )
                    await s_other.commit()
            except Exception:
                pass

    return True, None