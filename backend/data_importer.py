# -*- coding: utf-8 -*-
import os
import sys
import io
import datetime
import pyodbc
import psycopg2
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine, text
from database import load_config, save_config, build_sync_url, switch_database

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_FILE_PATH = os.path.join(LOGS_DIR, "import.log")

def append_to_log_file(line: str):
    """向日志文件追加一行记录"""
    try:
        os.makedirs(LOGS_DIR, exist_ok=True)
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{now_str}] {line}\n")
    except Exception as e:
        print(f"写入日志文件失败: {e}")

# 全局导入进度状态跟踪
import_status = {
    "is_running": False,
    "percent": 0,
    "message": "空闲",
    "current_action": "当前无入库任务运行",
    "details": [],
    "summary": None,
    "error": None,
    "log_file": "logs/import.log"
}

def update_progress(percent: int, message: str, log_item: str = None, action: str = None):
    global import_status
    import_status["percent"] = percent
    import_status["message"] = message
    if action:
        import_status["current_action"] = action
    elif log_item:
        import_status["current_action"] = log_item
    else:
        import_status["current_action"] = message

    if log_item:
        import_status["details"].append(log_item)
        append_to_log_file(log_item)
        print(f"[{percent}%] {log_item}")
    else:
        append_to_log_file(message)

def get_import_progress():
    return import_status

def ensure_database_and_tables(db_name: str, cfg: dict):
    """如果目标数据库不存在则创建，并初始化业务表与系统用户"""
    user = cfg.get("db_user", "postgres")
    pwd = cfg.get("db_pass", "123456")
    host = cfg.get("db_host", "localhost")
    port = cfg.get("db_port", 5432)

    # 1. 连接 postgres 默认库检查目标数据库
    admin_conn = psycopg2.connect(
        user=user, password=pwd, host=host, port=port, database="postgres"
    )
    admin_conn.autocommit = True
    admin_cur = admin_conn.cursor()
    
    admin_cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
    exists = admin_cur.fetchone()
    if not exists:
        # 针对包含中文字符的数据库名加上安全引号
        safe_db_name = db_name.replace('"', '""')
        admin_cur.execute(f'CREATE DATABASE "{safe_db_name}" ENCODING "UTF8"')
        print(f"创建数据库成功: {db_name}")
    admin_cur.close()
    admin_conn.close()

    # 2. 连接新创建或已有的目标库，初始化系统表结构
    target_conn = psycopg2.connect(
        user=user, password=pwd, host=host, port=port, database=db_name
    )
    target_conn.autocommit = True
    cur = target_conn.cursor()

    init_sql = """
    CREATE TABLE IF NOT EXISTS sys_users (
        id SERIAL PRIMARY KEY,
        username VARCHAR NOT NULL,
        password VARCHAR NOT NULL,
        role VARCHAR NOT NULL DEFAULT 'user',
        created_at TIMESTAMP DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS sys_permissions (
        username VARCHAR PRIMARY KEY,
        perms JSONB NOT NULL DEFAULT '{}'::jsonb
    );

    CREATE TABLE IF NOT EXISTS waiye_samples (
        id SERIAL PRIMARY KEY,
        township_name VARCHAR,
        village_name VARCHAR,
        group_name VARCHAR,
        group_code VARCHAR,
        cbfmc VARCHAR,
        cbfbm VARCHAR,
        cbfbm_short VARCHAR,
        lxdh VARCHAR,
        dkmc VARCHAR,
        dkbm VARCHAR,
        dkbm_short VARCHAR,
        scmj NUMERIC,
        area_acknowledged VARCHAR DEFAULT '',
        rights_correct VARCHAR DEFAULT '',
        bound_correct VARCHAR DEFAULT '',
        member_qualified VARCHAR DEFAULT '',
        self_verified VARCHAR DEFAULT '',
        self_signed VARCHAR DEFAULT '',
        satisfaction VARCHAR DEFAULT '满意',
        survey_method VARCHAR DEFAULT '现场',
        created_at TIMESTAMP DEFAULT now(),
        updated_at TIMESTAMP DEFAULT now(),
        signature_url VARCHAR DEFAULT '',
        phone_correct VARCHAR DEFAULT ''
    );

    CREATE TABLE IF NOT EXISTS neiye_records (
        id SERIAL PRIMARY KEY,
        qsdwdm VARCHAR NOT NULL UNIQUE,
        qsdwmc VARCHAR,
        level VARCHAR,
        form_data JSONB,
        score NUMERIC,
        updated_at TIMESTAMP DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS contractor_signatures (
        cbfbm VARCHAR PRIMARY KEY,
        cbfmc VARCHAR,
        signature_path VARCHAR,
        signature_data TEXT,
        updated_at TIMESTAMP DEFAULT now()
    );

    CREATE TABLE IF NOT EXISTS waiye_inquiries (
        id SERIAL PRIMARY KEY,
        cbfbm VARCHAR NOT NULL,
        township_name VARCHAR,
        village_name VARCHAR,
        group_name VARCHAR,
        cbfmc VARCHAR,
        form_data JSONB,
        signature_url TEXT,
        scan_file_url TEXT,
        updated_at TIMESTAMP DEFAULT now()
    );

    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'neiye_records_qsdwdm_key'
        ) THEN
            ALTER TABLE neiye_records ADD CONSTRAINT neiye_records_qsdwdm_key UNIQUE (qsdwdm);
        END IF;
    END $$;
    """
    cur.execute(init_sql)

    # 3. 初始化默认管理员账号（若不存在）
    from auth import _hash_pwd, DEFAULT_PERMS
    import json
    cur.execute("SELECT 1 FROM sys_users WHERE username = 'admin'")
    if not cur.fetchone():
        admin_pwd = _hash_pwd("admin123")
        cur.execute("INSERT INTO sys_users (username, password, role) VALUES (%s, %s, %s)", ("admin", admin_pwd, "admin"))
        cur.execute("INSERT INTO sys_permissions (username, perms) VALUES (%s, %s)", ("admin", json.dumps(DEFAULT_PERMS)))
    
    cur.execute("SELECT 1 FROM sys_users WHERE username = 'user'")
    if not cur.fetchone():
        user_pwd = _hash_pwd("123456")
        cur.execute("INSERT INTO sys_users (username, password, role) VALUES (%s, %s, %s)", ("user", user_pwd, "user"))
        cur.execute("INSERT INTO sys_permissions (username, perms) VALUES (%s, %s)", ("user", json.dumps(DEFAULT_PERMS)))

    cur.close()
    target_conn.close()

def query_import_summary(engine):
    """查询导入后的统计信息：乡镇数、村数、组数、农户数、地块数"""
    summary = {
        "township_count": 0,
        "village_count": 0,
        "group_count": 0,
        "farmer_count": 0,
        "parcel_count": 0,
        "townships": []
    }
    with engine.connect() as conn:
        try:
            r = conn.execute(text("SELECT qsdwdm, qsdwmc FROM qsdwdmb ORDER BY qsdwdm"))
            rows = r.fetchall()
            ts_list = []
            v_cnt = 0
            g_cnt = 0
            for row in rows:
                code = str(row[0])
                name = str(row[1])
                if code.endswith('00000') and not code.endswith('00000000'):
                    ts_list.append(name)
                elif code.endswith('00') and not code.endswith('00000'):
                    v_cnt += 1
                elif not code.endswith('00'):
                    g_cnt += 1
            summary["township_count"] = len(ts_list)
            summary["village_count"] = v_cnt
            summary["group_count"] = g_cnt
            summary["townships"] = ts_list
        except Exception as e:
            print(f"统计代码表异常: {e}")

        try:
            r_cbf = conn.execute(text("SELECT COUNT(*) FROM cbf"))
            summary["farmer_count"] = r_cbf.scalar() or 0
        except Exception as e:
            print(f"统计农户数异常: {e}")

        try:
            r_dk = conn.execute(text("SELECT COUNT(*) FROM cbdkxx"))
            summary["parcel_count"] = r_dk.scalar() or 0
        except Exception as e:
            print(f"统计地块数异常: {e}")

    return summary

def validate_source_package(source_dir: str):
    """
    入库前校验必要文件夹与必要文件：
    1. 检查必要文件夹“权属数据”和“矢量数据”是否存在且命名正确
    2. “权属数据”中必须存在 .mdb 文件和权属单位代码表 (.xls/.xlsx)
    3. “矢量数据”中必须存在文件名包含“*DK*”的 .shp 矢量文件
    """
    if not source_dir or not os.path.exists(source_dir) or not os.path.isdir(source_dir):
        return False, f"找不到指定的数据包根目录: {source_dir}", {}

    qs_folder = os.path.join(source_dir, '权属数据')
    if not os.path.exists(qs_folder) or not os.path.isdir(qs_folder):
        return False, "缺少必要文件夹【权属数据】或文件夹未按规范命名为“权属数据”", {}

    shp_folder = os.path.join(source_dir, '矢量数据')
    if not os.path.exists(shp_folder) or not os.path.isdir(shp_folder):
        return False, "缺少必要文件夹【矢量数据】或文件夹未按规范命名为“矢量数据”", {}

    # 校验【权属数据】中的 mdb 文件
    qs_files = os.listdir(qs_folder)
    mdb_files = [f for f in qs_files if f.lower().endswith('.mdb') and not f.startswith('~')]
    if not mdb_files:
        return False, "【权属数据】文件夹中必须存在 .mdb 权属数据库文件，未检测到有效 mdb 文件", {}
    mdb_path = os.path.join(qs_folder, mdb_files[0])

    # 校验【权属数据】中的权属单位代码表
    xls_files = [f for f in qs_files if (f.lower().endswith('.xls') or f.lower().endswith('.xlsx')) and not f.startswith('~')]
    code_table_files = [f for f in xls_files if ("代码表" in f or "权属单位" in f)]
    if not code_table_files:
        # 如果未明确带有“代码表”字样但有excel，亦尝试作为备选，否则报错
        if xls_files:
            code_table_files = xls_files
        else:
            return False, "【权属数据】文件夹中必须存在【权属单位代码表】(Excel格式 .xls 或 .xlsx)，未检测到代码表文件", {}
    xls_path = os.path.join(qs_folder, code_table_files[0])

    # 校验【矢量数据】中包含 *DK* 的矢量文件 (.shp)
    shp_files_all = os.listdir(shp_folder)
    dk_shp_files = [f for f in shp_files_all if f.lower().endswith('.shp') and ('dk' in f.lower() or '地块' in f)]
    if not dk_shp_files:
        return False, "【矢量数据】文件夹中必须存在文件名包含“DK”的矢量文件 (例如 DK341124100.shp)，未检测到符合条件的 .shp 文件", {}
    shp_path = os.path.join(shp_folder, dk_shp_files[0])

    return True, "", {
        "qs_folder": qs_folder,
        "shp_folder": shp_folder,
        "mdb_path": mdb_path,
        "xls_path": xls_path,
        "shp_path": shp_path
    }

def import_data_from_path(source_dir: str, county_name: str = None):
    global import_status
    import_status = {
        "is_running": True,
        "percent": 0,
        "message": "正在核验数据包规范性...",
        "current_action": "开始检查数据包目录与必要文件...",
        "details": [],
        "summary": None,
        "error": None,
        "log_file": "logs/import.log"
    }

    # 1. 严格校验数据包文件夹与必要文件
    update_progress(3, "正在检查必要文件夹与必要文件完整性...", "开始检查数据包目录结构...", action="检查文件夹规范：【权属数据】与【矢量数据】")
    is_valid, err_msg, file_info = validate_source_package(source_dir)
    if not is_valid:
        update_progress(100, "数据包校验未通过", f"【校验失败】{err_msg}", action=f"校验未通过: {err_msg}")
        import_status["error"] = err_msg
        import_status["is_running"] = False
        return import_status["details"], None

    shp_path = file_info["shp_path"]
    mdb_path = file_info["mdb_path"]
    xls_path = file_info["xls_path"]
    update_progress(8, "数据包结构校验通过", f"数据包校验成功：检测到矢量文件 [{os.path.basename(shp_path)}]、权属文件 [{os.path.basename(mdb_path)}] 及代码表 [{os.path.basename(xls_path)}]", action="数据包前置校验通过，准备数据库环境")

    cfg = load_config()
    target_county = county_name.strip() if (county_name and county_name.strip()) else cfg.get("county_name", "全椒县")
    target_db = target_county

    try:
        update_progress(12, f"开始创建/校验数据库: {target_db}", f"准备数据库 [{target_db}] 环境...", action=f"正在检查/创建 PostgreSQL 数据库 [{target_db}]")
        try:
            ensure_database_and_tables(target_db, cfg)
            update_progress(18, f"数据库 [{target_db}] 环境就绪", f"数据库 [{target_db}] 初始化完成", action=f"数据库 [{target_db}] 系统表与管理员初始化就绪")
        except Exception as e:
            err_msg = f"初始化数据库环境失败: {e}"
            import_status["error"] = err_msg
            import_status["is_running"] = False
            update_progress(100, "失败", err_msg, action="初始化数据库环境失败")
            return import_status["details"], None

        # 构建同步连接引擎
        cfg["county_name"] = target_county
        cfg["db_name"] = target_db
        sync_url = build_sync_url(cfg)
        engine = create_engine(sync_url)

        # 1. 导入 SHP 属性数据
        update_progress(20, "正在解析 SHP 矢量属性数据...", f"发现矢量文件: {shp_path or '未找到'}", action=f"正在读取地块空间矢量文件 [{os.path.basename(shp_path)}]")
        if shp_path and os.path.exists(shp_path):
            try:
                gdf = gpd.read_file(shp_path)
                update_progress(35, "正在写入地块属性数据到数据库...", f"SHP 读取完成，包含 {len(gdf)} 个要素，正在剥离空间几何并入库...", action=f"正在将 {len(gdf)} 条地块矢量属性写入 dkxx_shp_attrs 表")
                df_shp = pd.DataFrame(gdf.drop(columns='geometry'))
                df_shp.columns = [c.lower() for c in df_shp.columns]
                if 'id' not in df_shp.columns:
                    df_shp.insert(0, 'id', range(1, 1 + len(df_shp)))
                df_shp.to_sql('dkxx_shp_attrs', engine, if_exists='replace', index=False, chunksize=1000)
                update_progress(45, "SHP 矢量属性数据入库成功", f"地块矢量属性 (dkxx_shp_attrs) 写入成功 (共 {len(df_shp)} 条)", action="地块矢量属性全量写入成功")
            except Exception as e:
                update_progress(45, "SHP 导入警告", f"SHP 导入失败: {e}", action="SHP 导入出现警告")
        else:
            update_progress(45, "跳过 SHP 属性", "未检测到 SHP 矢量数据文件，跳过", action="未检测到 SHP 矢量数据，跳过")

        # 2. 导入 MDB 权属数据
        update_progress(50, "正在连接并解析 MDB 权属数据库...", f"发现 MDB 文件: {mdb_path or '未找到'}", action=f"正在连接 Access 权属数据库 [{os.path.basename(mdb_path)}]")
        if mdb_path and os.path.exists(mdb_path):
            try:
                conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + mdb_path + ';'
                with pyodbc.connect(conn_str) as conn:
                    cursor = conn.cursor()
                    tables = [table.table_name for table in cursor.tables(tableType='TABLE')]
                    valid_tables = [t for t in tables if not t.startswith('~')]
                    total_t = len(valid_tables)
                    update_progress(55, f"MDB 包含 {total_t} 张数据表，开始逐表写入...", f"MDB 数据表列表: {', '.join(valid_tables[:6])}...", action=f"开始批量写入 MDB 中的 {total_t} 张数据表")
                    
                    for idx, table in enumerate(valid_tables):
                        try:
                            df = pd.read_sql(f'SELECT * FROM [{table}]', conn)
                            df.columns = [c.lower() for c in df.columns]
                            row_cnt = len(df)
                            df.to_sql(table.lower(), engine, if_exists='replace', index=False, chunksize=1000)
                            cur_pct = 55 + int(25 * (idx + 1) / max(total_t, 1))
                            action_text = f"正在写入表 [{table}] ({row_cnt} 行，进度 {idx+1}/{total_t})"
                            update_progress(cur_pct, f"表 [{table}] 入库完成 ({row_cnt} 行)", f"MDB 表 [{table}] 入库成功 (共 {row_cnt} 条)", action=action_text)
                        except Exception as te:
                            print(f"导入表 {table} 异常: {te}")
                update_progress(80, "MDB 权属数据入库成功", f"MDB 权属数据全量写入成功 (共 {total_t} 张表)", action=f"MDB 权属数据 {total_t} 张表全部入库完成")
            except Exception as e:
                update_progress(80, "MDB 导入警告", f"MDB 权属数据导入失败: {e}", action="MDB 权属导入警告")
        else:
            update_progress(80, "跳过 MDB 导入", "未检测到 MDB 权属数据库，跳过", action="跳过 MDB 导入")

        # 3. 导入 XLS 权属代码表
        update_progress(85, "正在导入权属单位代码表...", f"发现代码表文件: {xls_path or '未找到'}", action=f"正在解析权属代码表 [{os.path.basename(xls_path)}]")
        if xls_path and os.path.exists(xls_path):
            try:
                df_xls = pd.read_excel(xls_path)
                df_xls.rename(columns={'权属单位代码': 'qsdwdm', '权属单位名称': 'qsdwmc'}, inplace=True)
                df_xls.to_sql('qsdwdmb', engine, if_exists='replace', index=False)
                update_progress(92, "代码表写入完成", f"权属单位代码表 (qsdwdmb) 写入成功 (共 {len(df_xls)} 行)", action=f"权属代码表写入成功 (共 {len(df_xls)} 级区划)")
            except Exception as e:
                update_progress(92, "XLS 导入警告", f"XLS 代码表导入失败: {e}", action="XLS 导入警告")
        else:
            update_progress(92, "跳过代码表", "未检测到 XLS 代码表，跳过", action="跳过代码表导入")

        # 4. 汇总统计
        update_progress(95, "正在汇总统计入库成果...", "开始统计乡镇、村组及农户、地块数量...", action="正在执行全量数据库成果多维统计")
        summary = query_import_summary(engine)
        
        # 5. 切换系统当前主数据库连接并持久化到 config.json
        switch_database(target_db, target_county)

        summary_log = f"入库完成统计：共入库 {summary['township_count']} 个乡镇、{summary['village_count']} 个行政村、{summary['group_count']} 个村民组、{summary['farmer_count']} 户承包方、{summary['parcel_count']} 宗地块。"
        update_progress(100, "全量数据入库完成！", summary_log, action="全部数据已安全入库完成并切换为当前数据库")
        
        import_status["is_running"] = False
        import_status["summary"] = summary
        return import_status["details"], summary
    except Exception as e:
        err_msg = f"入库处理发生未预期的异常: {e}"
        print(err_msg)
        import_status["error"] = err_msg
        import_status["is_running"] = False
        update_progress(100, "入库异常中断", err_msg, action=f"异常中断: {err_msg}")
        return import_status["details"], None
