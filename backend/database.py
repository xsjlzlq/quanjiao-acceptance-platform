import os
import json
import psycopg2
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

DEFAULT_CONFIG = {
    "county_name": "全椒县",
    "db_name": "quanjiao",
    "db_host": "localhost",
    "db_port": 5432,
    "db_user": "postgres",
    "db_pass": "123456",
    "base_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
}

def get_base_dir() -> str:
    """从 config.json 读取系统基础根目录 base_dir，具备安全自动回退机制"""
    cfg = load_config()
    b_dir = cfg.get("base_dir")
    if b_dir and os.path.exists(b_dir):
        return os.path.abspath(b_dir)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def load_config() -> dict:
    """从 config.json 读取数据库配置，若不存在则创建默认配置"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return {**DEFAULT_CONFIG, **cfg}
        except Exception as e:
            print(f"Error loading config.json: {e}")
    else:
        save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    """持久化保存配置到 config.json"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

import os
import json
import psycopg2
import contextvars
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine, text

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

# 请求级别当前数据库上下文，不同异步请求完全隔离互不串库
current_db_ctx = contextvars.ContextVar("current_db_ctx", default="")

DEFAULT_CONFIG = {
    "county_name": "全椒县",
    "db_name": "quanjiao",
    "db_host": "localhost",
    "db_port": 5432,
    "db_user": "postgres",
    "db_pass": "123456",
    "base_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
}

def get_base_dir() -> str:
    """从 config.json 读取系统基础根目录 base_dir，具备安全自动回退机制"""
    cfg = load_config()
    b_dir = cfg.get("base_dir")
    if b_dir and os.path.exists(b_dir):
        return os.path.abspath(b_dir)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def load_config() -> dict:
    """从 config.json 读取数据库配置，若不存在则创建默认配置"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                return {**DEFAULT_CONFIG, **cfg}
        except Exception as e:
            print(f"Error loading config.json: {e}")
    else:
        save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()

def save_config(cfg: dict):
    """持久化保存配置到 config.json"""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

def build_async_url(cfg: dict, db_name: str = None) -> str:
    db = db_name if db_name else cfg.get("db_name", "quanjiao")
    user = cfg.get("db_user", "postgres")
    pwd = cfg.get("db_pass", "123456")
    host = cfg.get("db_host", "localhost")
    port = cfg.get("db_port", 5432)
    return f"postgresql+asyncpg://{user}:{pwd}@{host}:{port}/{db}"

def build_sync_url(cfg: dict, db_name: str = None) -> str:
    db = db_name if db_name else cfg.get("db_name", "quanjiao")
    user = cfg.get("db_user", "postgres")
    pwd = cfg.get("db_pass", "123456")
    host = cfg.get("db_host", "localhost")
    port = cfg.get("db_port", 5432)
    return f"postgresql://{user}:{pwd}@{host}:{port}/{db}"

def list_available_databases() -> list:
    """查询 PostgreSQL 中所有非模板/非系统数据库"""
    cfg = load_config()
    user = cfg.get("db_user", "postgres")
    pwd = cfg.get("db_pass", "123456")
    host = cfg.get("db_host", "localhost")
    port = cfg.get("db_port", 5432)
    try:
        conn = psycopg2.connect(
            user=user, password=pwd, host=host, port=port, database="postgres"
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT datname 
            FROM pg_database 
            WHERE datistemplate = false 
              AND datname NOT IN ('postgres')
            ORDER BY datname
        """)
        dbs = [r[0] for r in cur.fetchall()]
        cur.close()
        conn.close()
        return dbs
    except Exception as e:
        print(f"获取数据库列表失败: {e}")
        return []

def parse_qsdwdmb_hierarchy(rows):
    """
    解析 qsdwdmb 的 (qsdwdm, qsdwmc) 结果集
    返回:
      county: {"code": "341124", "name": "全椒县", "full_code": "34112400000000"}
      townships: [{"code": "341124100", "name": "襄河镇", "full_code": "..."}, ...]
    """
    county = None
    townships = []
    for r in rows:
        code = str(r[0]).strip()
        name = str(r[1]).strip()
        if code.endswith('00000000'):
            clean_name = name.replace("安徽省", "").replace("滁州市", "")
            county = {"code": code[:6], "name": clean_name, "full_code": code}
        elif code.endswith('00000') and not code.endswith('00000000'):
            townships.append({"code": code[:9], "name": name, "full_code": code})
    
    cfg = load_config()
    if not county:
        county = {
            "code": townships[0]["code"][:6] if townships else "341124",
            "name": cfg.get("county_name", "全椒县"),
            "full_code": (townships[0]["code"][:6] + "00000000") if townships else "34112400000000"
        }
    return county, townships

def get_county_and_townships_sync(engine=None, db_name=None):
    """同步从指定数据库的 qsdwdmb 中解析县级信息与乡镇列表"""
    if engine is None:
        cfg = load_config()
        target_db = db_name or current_db_ctx.get() or cfg.get("db_name", "quanjiao")
        sync_url = build_sync_url(cfg, db_name=target_db)
        engine = create_engine(sync_url)
    with engine.connect() as conn:
        try:
            res = conn.execute(text("SELECT qsdwdm, qsdwmc FROM qsdwdmb ORDER BY qsdwdm"))
            rows = res.fetchall()
            return parse_qsdwdmb_hierarchy(rows)
        except Exception as e:
            print(f"读取 qsdwdmb 失败或表尚未导入: {e}")
            cfg = load_config()
            target_county = cfg.get("county_name", "全椒县") if not db_name else db_name
            return {"code": "341124", "name": target_county, "full_code": "34112400000000"}, []

# ================= 多租户连接池与动态路由 =================
_async_engines = {}
_sync_engines = {}
_session_factories = {}

def get_engine_for_db(db_name: str = None):
    """获取或初始化指定数据库的异步连接池"""
    cfg = load_config()
    target_db = (db_name or current_db_ctx.get() or cfg.get("db_name", "quanjiao")).strip()
    if target_db not in _async_engines:
        url = build_async_url(cfg, db_name=target_db)
        _async_engines[target_db] = create_async_engine(url, echo=False, pool_pre_ping=True)
    return _async_engines[target_db]

def get_session_factory(db_name: str = None):
    """获取指定数据库的会话工厂"""
    cfg = load_config()
    target_db = (db_name or current_db_ctx.get() or cfg.get("db_name", "quanjiao")).strip()
    if target_db not in _session_factories:
        eng = get_engine_for_db(target_db)
        _session_factories[target_db] = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    return _session_factories[target_db]

class DynamicSessionLocal:
    """
    智能动态会话管理器：
    在任何地方执行 `async with SessionLocal() as session:` 或 `SessionLocal()` 时，
    自动检测当前异步请求的上下文数据库 `current_db_ctx.get()`，
    从而精准连接该账号被授权的目标数据库，保证不同账号并发操作互不串库！
    """
    def __call__(self, *args, **kwargs):
        db_override = kwargs.pop("db_name", None)
        factory = get_session_factory(db_override)
        return factory(*args, **kwargs)

    def configure(self, **kwargs):
        # 兼容老调用
        pass

# 导出供外部使用的对象
current_cfg = load_config()
SessionLocal = DynamicSessionLocal()
engine = get_engine_for_db(current_cfg.get("db_name", "quanjiao"))
Base = declarative_base()

def switch_database(db_name: str, county_name: str = ""):
    """切换当前应用全局默认数据库，并持久化保存至 config.json"""
    global engine, current_cfg
    cfg = load_config()
    cfg["db_name"] = db_name
    if county_name:
        cfg["county_name"] = county_name
    elif not cfg.get("county_name"):
        cfg["county_name"] = db_name
    save_config(cfg)
    current_cfg = cfg
    engine = get_engine_for_db(db_name)
    print(f"[DB] 全局默认数据库已设置为: [{db_name}] (县域: {cfg.get('county_name')})")

async def get_db():
    async with SessionLocal() as session:
        yield session
