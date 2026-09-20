import base64
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
import uuid
import shutil, io
from collections import defaultdict
from PIL import Image, ImageOps
from doc_exporter import (
    export_docs, export_att4, export_att5, export_waiye_att8, export_waiye_att9,
    export_neiye_att6_township, export_neiye_att6_county, export_neiye_att7,
    export_neiye_att6_mechanism_only,
    export_rectify_att12, export_rectify_att13, sanitize_filename,
    export_sample_detail_excel, export_village_meeting_photos
)
# -*- coding: utf-8 -*-
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import os
import time
import datetime
import random
import math
import json
import pandas as pd
from sqlalchemy import text, create_engine
from database import (
    SessionLocal, load_config, switch_database, list_available_databases,
    build_sync_url, parse_qsdwdmb_hierarchy, get_base_dir, current_db_ctx,
    get_county_and_townships_sync
)
from data_importer import import_data_from_path, get_import_progress, query_import_summary, ensure_database_and_tables, validate_source_package
import auth as auth_module
from audit_logger import record_check_audit

from batch_exporter import (
    run_batch_export, export_tasks, get_export_task_progress,
    set_export_task_init, update_export_task
)

app = FastAPI(title="全椒县二轮延包验收系统 API")

@app.get("/api/select_export_dir")
async def api_select_export_dir():
    import subprocess
    import asyncio
    
    def _pick_dir():
        ps_script = """
        [System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms") | Out-Null
        $folderBrowser = New-Object System.Windows.Forms.FolderBrowserDialog
        $folderBrowser.Description = "请选择导出存放目录"
        $folderBrowser.ShowNewFolderButton = $true
        
        $form = New-Object System.Windows.Forms.Form
        $form.TopMost = $true
        
        $result = $folderBrowser.ShowDialog($form)
        if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
            Write-Output $folderBrowser.SelectedPath
        }
        """
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            return result.stdout.strip()
        except Exception as e:
            print("Folder picker error:", e)
            return ""
            
    folder_path = await asyncio.to_thread(_pick_dir)
    if folder_path:
        return {"code": 200, "path": folder_path}
    return {"code": 400, "message": "已取消选择"}

class BatchExportRequest(BaseModel):
    level: str
    township_code: str = ""
    township_name: str = ""
    attachments: List[str] = []

@app.post("/api/batch_export")
async def api_batch_export(req: BatchExportRequest):
    """
    异步启动批量打包任务，防止大附件生成导致前端 HTTP 524/Timeout 超时。
    立即返回 task_id，前端轮询 /api/batch_export/progress。
    """
    import uuid
    task_id = uuid.uuid4().hex
    set_export_task_init(task_id)

    async def _async_worker():
        try:
            await run_batch_export(
                req.level, req.township_code, req.township_name, req.attachments, task_id=task_id
            )
        except Exception as err:
            update_export_task(task_id, 100, f"打包失败: {str(err)}", error=str(err))

    # 后台异步执行
    asyncio.create_task(_async_worker())
    return {"code": 200, "message": "批量打包任务已在后台启动", "task_id": task_id}

@app.get("/api/batch_export/progress")
async def api_batch_export_progress(task_id: str):
    """
    轮询批量打包任务的实时百分比与当前处理步骤
    """
    prog = get_export_task_progress(task_id)
    return {"code": 200, "data": prog}

@app.on_event("startup")
async def startup_event():
    await auth_module.init_auth_db()
    
    # 自动遍历现有可用数据库，统一自愈补齐用户表字段，彻底根治 500 报错
    try:
        all_dbs = await asyncio.to_thread(list_available_databases)
        for db in all_dbs:
            try:
                async with SessionLocal(db_name=db) as s_db:
                    await auth_module.ensure_user_table_schema(s_db)
            except Exception:
                pass
    except Exception as e:
        print(f"Startup multi-db migration error: {e}")

    try:
        async with SessionLocal() as s:
            await s.execute(text("""
                DO $$
                BEGIN
                    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'neiye_records') THEN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_constraint WHERE conname = 'neiye_records_qsdwdm_key'
                        ) THEN
                            ALTER TABLE neiye_records ADD CONSTRAINT neiye_records_qsdwdm_key UNIQUE (qsdwdm);
                        END IF;
                    END IF;
                END $$;
            """))
            await s.commit()
    except Exception as e:
        print(f"Startup constraint check error: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def dynamic_db_router_middleware(request: Request, call_next):
    """
    多租户动态数据库路由器中间件（安全加固版）：
    1. 若请求携带有效普通用户 Token，强制锁定其绑定的 target_db，杜绝客户端请求头覆盖或篡改；
    2. 若用户为管理员 (role == 'admin')，允许根据客户端 X-Database 或全局设置灵活动态切库；
    3. 公共/未登录请求默认采用请求头 X-Database 或 config.json 中的数据库。
    将解析出的数据库绑定至当前请求的协程 ContextVar 中，实现多账号不同库完全隔离！
    """
    raw_target_db = request.headers.get("X-Database", "").strip()
    client_db = ""
    if raw_target_db:
        import urllib.parse
        client_db = urllib.parse.unquote(raw_target_db).strip()

    target_db = ""
    # 1. 尝试从合法 Token 中解析身份
    auth_hdr = request.headers.get("Authorization", "")
    if auth_hdr.startswith("Bearer "):
        raw_token = auth_hdr.split(" ", 1)[1].strip()
        payload = auth_module._verify_token(raw_token)
        if payload:
            role = payload.get("role", "user")
            bound_db = (payload.get("target_db") or "").strip()
            # 普通用户：最高权威，强制使用 Token 内部绑定的数据库，绝不允许被客户端 Header 污染！
            if role != "admin" and bound_db:
                target_db = bound_db
            # 管理员用户：若传了 client_db 则优先使用，以支持管理员在前端自由切换库
            elif role == "admin" and client_db:
                target_db = client_db
            elif bound_db:
                target_db = bound_db

    # 2. 未能从 Token 判定的情况（如未登录或管理员未指定库），采用客户端指定库或系统默认库
    if not target_db and client_db:
        target_db = client_db

    if not target_db:
        cfg = load_config()
        target_db = cfg.get("db_name", "quanjiao")

    token_ctx = current_db_ctx.set(target_db)
    try:
        response = await call_next(request)
        import urllib.parse
        response.headers["X-Active-Database"] = urllib.parse.quote(str(target_db))
        return response
    finally:
        current_db_ctx.reset(token_ctx)

@app.get("/")
async def root():
    return {"message": "Welcome to 全椒县二轮延包验收系统 API"}

@app.get("/api/system/available_dbs")
async def api_get_available_dbs():
    dbs = await asyncio.to_thread(list_available_databases)
    cfg = load_config()
    return {"code": 200, "databases": dbs, "default_db": cfg.get("db_name", "quanjiao")}

class ImportRequest(BaseModel):
    source_path: str
    county_name: Optional[str] = None

class SwitchDbRequest(BaseModel):
    db_name: str
    county_name: Optional[str] = None

@app.get("/api/system/db_config")
async def api_get_db_config():
    cfg = load_config()
    current_db = cfg.get("db_name", "quanjiao")
    
    # 动态从数据库代码表中解析权威中文县名
    county_info, _ = await asyncio.to_thread(get_county_and_townships_sync, None, current_db)
    county_name = county_info.get("name") if county_info and county_info.get("name") else cfg.get("county_name", current_db)
    
    base_dir = get_base_dir()
    available_dbs = await asyncio.to_thread(list_available_databases)
    
    def _get_summary():
        try:
            sync_url = build_sync_url(cfg)
            eng = create_engine(sync_url)
            return query_import_summary(eng)
        except Exception as e:
            print(f"获取当前库统计失败: {e}")
            return None

    summary = await asyncio.to_thread(_get_summary)
    return {
        "code": 200,
        "data": {
            "current_db": current_db,
            "county_name": county_name,
            "base_dir": base_dir,
            "available_dbs": available_dbs,
            "summary": summary
        }
    }

@app.post("/api/system/switch_db")
async def api_switch_db(req: SwitchDbRequest):
    target_db = req.db_name.strip()
    if not target_db:
        return {"code": 400, "message": "数据库名不能为空"}
    
    available_dbs = await asyncio.to_thread(list_available_databases)
    if target_db not in available_dbs:
        return {"code": 404, "message": f"未在 PostgreSQL 实例中找到数据库 [{target_db}]"}
    
    cfg = load_config()
    
    # 优先解析该库代码表中的权威中文县名，避免将拼音作为县名
    county_info, _ = await asyncio.to_thread(get_county_and_townships_sync, None, target_db)
    parsed_name = county_info.get("name") if county_info else ""
    
    if req.county_name and req.county_name.strip():
        target_county = req.county_name.strip()
    elif parsed_name:
        target_county = parsed_name
    else:
        target_county = target_db
    
    # 确保所选库存在基础系统表
    await asyncio.to_thread(ensure_database_and_tables, target_db, cfg)
    
    # 执行热切换并保存至 config.json
    switch_database(target_db, target_county)
    
    def _get_summary():
        try:
            sync_url = build_sync_url(load_config())
            eng = create_engine(sync_url)
            return query_import_summary(eng)
        except Exception:
            return None
            
    summary = await asyncio.to_thread(_get_summary)
    return {
        "code": 200,
        "message": f"系统已成功切换连接至数据库 [{target_db}]！",
        "data": {
            "current_db": target_db,
            "county_name": target_county,
            "summary": summary
        }
    }

@app.get("/api/import-progress")
async def api_import_progress():
    progress = get_import_progress()
    return {"code": 200, "data": progress}

@app.get("/api/audit-log/download")
async def api_download_audit_log():
    from fastapi.responses import FileResponse
    log_path = os.path.join(os.path.dirname(__file__), "logs", "check_audit.log")
    if os.path.exists(log_path):
        return FileResponse(log_path, filename="check_audit.log", media_type="text/plain; charset=utf-8")
    return {"code": 404, "message": "暂无核查审计日志文件"}

@app.get("/api/import-log/download")
async def api_download_import_log():
    from fastapi.responses import FileResponse
    log_path = os.path.join(os.path.dirname(__file__), "logs", "import.log")
    if os.path.exists(log_path):
        return FileResponse(log_path, filename="import.log", media_type="text/plain; charset=utf-8")
    return {"code": 404, "message": "暂无日志文件"}

@app.post("/api/import-data")
async def api_import_data(req: ImportRequest):
    path = req.source_path
    county = req.county_name
    if not os.path.exists(path):
        return {"code": 404, "message": f"找不到指定的数据包路径: {path}"}
    
    # 检查是否已有任务正在运行
    curr_progress = get_import_progress()
    if curr_progress.get("is_running"):
        return {"code": 400, "message": "当前已有数据包正在后台入库中，请等待其处理完成！"}
    
    # 同步前置校验必要文件夹及文件规范（耗时 < 0.05 秒）
    is_valid, err_msg, _ = validate_source_package(path)
    if not is_valid:
        return {"code": 400, "message": err_msg}
    
    # 启动后台非阻塞入库任务，彻底避免 HTTP 524 代理超时
    asyncio.create_task(asyncio.to_thread(import_data_from_path, path, county))
    
    return {
        "code": 200,
        "message": "数据包结构校验通过，已成功启动后台入库任务！",
        "data": { "is_running": True }
    }

@app.get("/api/villages")
async def get_villages():
    async with SessionLocal() as session:
        result = await session.execute(text("SELECT qsdwdm, qsdwmc FROM qsdwdmb ORDER BY qsdwdm"))
        rows = result.fetchall()
        data = [{"code": str(r[0]), "name": r[1]} for r in rows]
        return {"code": 200, "data": data}

@app.get("/api/contractors")
async def get_contractors(qsdwdm: str):
    clean_code = str(qsdwdm or "").strip()
    search_prefix = clean_code

    async with SessionLocal() as session:
        # 智能容错：如果前端传入的是中文村名（如“大墅社区”或“大墅镇 - 大墅社区”），自动从 qsdwdmb 反查其真实 12~14 位区划代码
        if not clean_code.isdigit():
            target_vname = clean_code.split(" - ")[-1].strip()
            row_v = await session.execute(
                text("SELECT qsdwdm FROM qsdwdmb WHERE qsdwmc = :name AND qsdwdm::text LIKE '%00' LIMIT 1"),
                {"name": target_vname}
            )
            v_match = row_v.fetchone()
            if v_match:
                search_prefix = str(v_match[0])
            else:
                # 尝试模糊匹配村名
                row_v2 = await session.execute(
                    text("SELECT qsdwdm FROM qsdwdmb WHERE qsdwmc LIKE :name AND qsdwdm::text LIKE '%00' LIMIT 1"),
                    {"name": f"%{target_vname}%"}
                )
                v_match2 = row_v2.fetchone()
                if v_match2:
                    search_prefix = str(v_match2[0])

        # 如果是 14 位的行政村代码（以 00 结尾），截取前 12 位以匹配该村下所有组及承包方
        if len(search_prefix) == 14 and search_prefix.endswith("00"):
            search_prefix = search_prefix[:12]

        sql = text("""
            SELECT c.cbfbm, c.cbfmc, c.lxdh, COALESCE(q.qsdwmc, '') as group_name
            FROM cbf c
            LEFT JOIN qsdwdmb q ON SUBSTRING(c.cbfbm::text, 1, 14) = q.qsdwdm::text
            WHERE c.cbfbm::text LIKE :code 
            ORDER BY c.cbfbm
        """)
        result = await session.execute(sql, {"code": f"{search_prefix}%"})
        rows = result.fetchall()
        data = [{
            "cbfbm": str(r[0]), 
            "cbfmc": r[1], 
            "lxdh": r[2] or "",
            "group_name": r[3] or ""
        } for r in rows]
        return {"code": 200, "data": data, "total": len(data), "search_prefix": search_prefix}

@app.get("/api/parcels")
async def get_parcels(cbfbm: str):
    async with SessionLocal() as session:
        sql = text("""
            SELECT a.dkbm, a.dkmc, a.scmj, a.dkdz, a.dkxz, a.dknz, a.dkbz 
            FROM dkxx_shp_attrs a
            JOIN cbdkxx b ON a.dkbm = b.dkbm
            WHERE b.cbfbm::text = :cbfbm
        """)
        result = await session.execute(sql, {"cbfbm": cbfbm})
        rows = result.fetchall()
        data = [{
            "dkbm": str(r[0]), "dkmc": r[1], "scmj": float(r[2]) if r[2] else 0.0,
            "dkdz": r[3], "dkxz": r[4], "dknz": r[5], "dkbz": r[6]
        } for r in rows]
        return {"code": 200, "data": data}

class WaiyeRecord(BaseModel):
    cbfbm: str
    dkbm: str
    result: dict
    timestamp: int

class SyncRequest(BaseModel):
    records: list[WaiyeRecord]

@app.post("/api/sync-waiye")
async def sync_waiye(req: SyncRequest):
    print(f"收到 {len(req.records)} 条外业核查数据")
    return {"code": 200, "message": f"成功同步 {len(req.records)} 条记录"}

@app.get("/api/hierarchy")
async def get_hierarchy():
    async with SessionLocal() as session:
        result = await session.execute(text("SELECT qsdwdm, qsdwmc FROM qsdwdmb ORDER BY qsdwdm"))
        rows = result.fetchall()
        
        county = None
        townships = []
        villages = []
        groups = []
        
        for r in rows:
            code = str(r[0])
            name = r[1]
            if code.endswith('00000000'):
                county = {"code": code[:6], "name": name.replace("安徽省", "").replace("滁州市", ""), "full_code": code}
            elif code.endswith('00000') and not code.endswith('00000000'):
                townships.append({"code": code[:9], "name": name, "full_code": code})
            elif code.endswith('00') and not code.endswith('00000'):
                villages.append({"code": code[:12], "name": name, "full_code": code, "parent": code[:9]})
            elif not code.endswith('00'):
                groups.append({"code": code, "name": name, "full_code": code, "parent": code[:12]})
                
        return {"code": 200, "county": county, "townships": townships, "villages": villages, "groups": groups}

@app.get("/api/neiye/townships")
async def get_neiye_townships():
    async with SessionLocal() as session:
        result = await session.execute(text("SELECT qsdwdm, qsdwmc FROM qsdwdmb ORDER BY qsdwdm"))
        rows = result.fetchall()
        
        county = None
        townships = []
        for r in rows:
            code = str(r[0])
            name = r[1]
            if code.endswith('00000000'):
                county = {"code": code[:6], "name": name.replace("安徽省", "").replace("滁州市", ""), "full_code": code}
            elif code.endswith('00000') and not code.endswith('00000000'):
                townships.append({"code": code[:9], "name": name, "full_code": code})
                
        if not county and townships:
            county = {"code": townships[0]["code"][:6], "name": "全椒县", "full_code": townships[0]["code"][:6] + "00000000"}

        # 动态从 waiye_samples 获取实际抽样的村列表
        res_sampled_v = await session.execute(text("""
            SELECT DISTINCT 
                w.township_name, 
                w.village_name, 
                SUBSTRING(w.group_code, 1, 12) || '00' as village_code
            FROM waiye_samples w
            WHERE w.village_name IS NOT NULL AND w.village_name != ''
            ORDER BY w.township_name, village_code
        """))
        sampled_villages = []
        for r in res_sampled_v.fetchall():
            t_name, v_name, v_code = r[0], r[1], str(r[2])
            sampled_villages.append({
                "code": v_code,
                "name": v_name,
                "township_name": t_name,
                "full_title": f"{t_name} - {v_name}",
                "level": "village"
            })

        res_sampled = await session.execute(text("SELECT DISTINCT township_name FROM waiye_samples"))
        sampled_names = set(r[0] for r in res_sampled.fetchall() if r[0])
        sampled_townships = [t for t in townships if t["name"] in sampled_names]

        return {
            "code": 200, 
            "county": county, 
            "townships": sampled_townships,
            "villages": sampled_villages
        }

@app.get("/api/contractor_count")
async def get_contractor_count(group_code: str):
    clean_code = str(group_code or "").strip()
    async with SessionLocal() as session:
        # 该发包方总承包方户数
        sql_total = text("SELECT COUNT(*) FROM cbf WHERE cbfbm::text LIKE :code")
        res_total = await session.execute(sql_total, {"code": f"{clean_code}%"})
        total_count = res_total.scalar() or 0

        # 该发包方已在 waiye_samples 中的去重承包方户数
        sql_sampled = text("SELECT COUNT(DISTINCT cbfbm) FROM waiye_samples WHERE group_code = :code")
        res_sampled = await session.execute(sql_sampled, {"code": clean_code})
        sampled_count = res_sampled.scalar() or 0

        remaining_count = max(total_count - sampled_count, 0)

        return {
            "code": 200, 
            "count": total_count,
            "sampled_count": sampled_count,
            "remaining_count": remaining_count
        }

class SampleRequest(BaseModel):
    mode: int
    township_code: str
    village_code: Optional[str] = None
    group_code: Optional[str] = None
    township_name: str
    village_name: Optional[str] = None
    group_name: Optional[str] = None
    manual_sample_count: Optional[int] = None
    township_codes: Optional[list] = None
    township_names: Optional[list] = None

def calc_sample_size(total_cbf: int, manual_count: int = None) -> int:
    if manual_count is not None and manual_count > 0:
        return min(total_cbf, manual_count)
    if total_cbf < 20:
        return total_cbf
    elif total_cbf <= 100:
        return random.randint(5, 10)
    else:
        return math.ceil(total_cbf * random.uniform(0.05, 0.10))

def check_group_sample_compliance(total_cbf: int, specified_count: Optional[int], group_desc: str = "") -> dict:
    """
    核验发包方指定的抽样户数是否符合抽样规范要求：
    - total_cbf < 20：规定应全部抽样
    - 20 <= total_cbf <= 100：规定抽样 5-10 户 (不足5户判定为不够)
    - total_cbf > 100：规定按 5%-10% 向上取整 (不足5%判定为不够)
    只有在抽样数不够（低于规定下限）或超过总人数时才标记 is_insufficient = True（强制拦截）。
    """
    res = {
        "is_specified": specified_count is not None and specified_count > 0,
        "specified_count": specified_count,
        "total_cbf": total_cbf,
        "required_min": 0,
        "required_max": 0,
        "required_desc": "",
        "status": "pass", # pass | insufficient | exceeded | overflow | zero | no_data | auto
        "is_insufficient": False,
        "shortage": 0,
        "message": "符合抽样要求",
        "summary_text": ""
    }

    if total_cbf == 0:
        if res["is_specified"]:
            res["status"] = "overflow"
            res["is_insufficient"] = True
            res["message"] = f"发包方数据库中暂无承包方数据，无法抽样"
            res["summary_text"] = f"{group_desc}：数据库中暂无承包农户数据，无法指定抽样"
        else:
            res["status"] = "no_data"
            res["message"] = "该发包方在系统中暂无承包方数据"
        return res

    # 留空未指定：由系统自动按规则计算，必然合规
    if not res["is_specified"]:
        res["status"] = "auto"
        res["is_insufficient"] = False
        if total_cbf < 20:
            res["required_min"] = total_cbf
            res["required_max"] = total_cbf
            res["required_desc"] = f"全部抽样 ({total_cbf}户)"
        elif total_cbf <= 100:
            res["required_min"] = 5
            res["required_max"] = min(10, total_cbf)
            res["required_desc"] = "5~10户"
        else:
            res["required_min"] = math.ceil(total_cbf * 0.05)
            res["required_max"] = min(total_cbf, math.ceil(total_cbf * 0.10))
            res["required_desc"] = f"5%~10% (即{res['required_min']}~{res['required_max']}户)"
        res["message"] = "未指定，系统将自动按规范足额抽样"
        return res

    # 指定了具体数值：开始比对合规性
    count = int(specified_count)

    if count <= 0:
        res["status"] = "zero"
        res["is_insufficient"] = True
        res["shortage"] = 1
        res["message"] = "指定的抽样户数不能为0或负数"
        res["summary_text"] = f"{group_desc}：指定的抽样数 ({count}户) 非法，不能为0或负数"
        return res

    if count > total_cbf:
        res["status"] = "overflow"
        res["is_insufficient"] = True
        res["shortage"] = 0
        res["message"] = f"指定抽样数 ({count}户) 超出实际总承包方数 ({total_cbf}户)"
        res["summary_text"] = f"{group_desc}：指定抽样数 ({count}户) 超过总户数 ({total_cbf}户)"
        return res

    if total_cbf < 20:
        res["required_min"] = total_cbf
        res["required_max"] = total_cbf
        res["required_desc"] = f"全额抽样 ({total_cbf}户)"
        if count < total_cbf:
            res["status"] = "insufficient"
            res["is_insufficient"] = True
            res["shortage"] = total_cbf - count
            res["message"] = f"总户数不足20户，按规定应全部抽样（需 {total_cbf} 户），当前仅指定 {count} 户（缺少 {res['shortage']} 户）"
            res["summary_text"] = f"{group_desc}：总户数 {total_cbf} 户（不足20户档次），规定应全部抽样 {total_cbf} 户，当前仅指定 {count} 户（缺少 {res['shortage']} 户）"
        else:
            res["status"] = "pass"

    elif total_cbf <= 100:
        res["required_min"] = 5
        res["required_max"] = min(10, total_cbf)
        res["required_desc"] = "5~10户"
        if count < 5:
            res["status"] = "insufficient"
            res["is_insufficient"] = True
            res["shortage"] = 5 - count
            res["message"] = f"总户数 20~100 户档次，按规定至少应抽样 5 户，当前仅指定 {count} 户（缺少 {res['shortage']} 户）"
            res["summary_text"] = f"{group_desc}：总户数 {total_cbf} 户（20~100户档次），规定至少抽样 5 户，当前仅指定 {count} 户（缺少 {res['shortage']} 户）"
        elif count > 10:
            res["status"] = "exceeded"
            res["is_insufficient"] = False # 超出建议上限不拦截
            res["message"] = f"高于建议上限：按规定抽样 5~10 户即可，当前指定 {count} 户（允许正常执行）"
        else:
            res["status"] = "pass"

    else:
        req_min = math.ceil(total_cbf * 0.05)
        req_max = min(total_cbf, math.ceil(total_cbf * 0.10))
        res["required_min"] = req_min
        res["required_max"] = req_max
        res["required_desc"] = f"5%~10% (即{req_min}~{req_max}户)"
        if count < req_min:
            res["status"] = "insufficient"
            res["is_insufficient"] = True
            res["shortage"] = req_min - count
            res["message"] = f"总户数 >100 户档次，按规定最低抽样 5% 向上取整（需 {req_min} 户），当前仅指定 {count} 户（缺少 {res['shortage']} 户）"
            res["summary_text"] = f"{group_desc}：总户数 {total_cbf} 户（>100户档次），规定至少抽样 5%（需 {req_min} 户），当前仅指定 {count} 户（缺少 {res['shortage']} 户）"
        elif count > req_max:
            res["status"] = "exceeded"
            res["is_insufficient"] = False # 超出建议上限不拦截
            res["message"] = f"高于建议上限：按规定抽样 5%~10%（{req_min}~{req_max}户）即可，当前指定 {count} 户（允许正常执行）"
        else:
            res["status"] = "pass"

    return res

@app.post("/api/sample")
async def do_sample(req: SampleRequest):
    async with SessionLocal() as session:
        sampled_groups = []
        if req.mode == 1:
            sampled_groups.append({"code": req.group_code, "name": req.group_name, "v_name": req.village_name, "tz_name": req.township_name})
        elif req.mode == 2:
            tz_list = []
            if req.township_codes and len(req.township_codes) > 0:
                tz_list = list(zip(req.township_codes, req.township_names))
            else:
                tz_list = [(req.township_code, req.township_name)]
            
            # 查询全县总乡镇数量
            r_cnt = await session.execute(text("SELECT COUNT(*) FROM qsdwdmb WHERE qsdwdm::text LIKE '%00000' AND qsdwdm::text NOT LIKE '%00000000'"))
            total_townships = r_cnt.scalar() or 0
            
            for tz_code, tz_name in tz_list:
                # 查询该乡镇下的组 (长度>=14)
                sql = text("SELECT qsdwdm, qsdwmc FROM qsdwdmb WHERE qsdwdm::text LIKE :ts AND LENGTH(qsdwdm::text) >= 14")
                res = await session.execute(sql, {"ts": f"{tz_code}%"})
                all_groups = res.fetchall()
                if not all_groups:
                    continue
                
                # 检查总乡镇数量，大于或等于10个乡镇随机选择2-5个组，小于10个随机选择3-6个组
                if total_townships >= 10:
                    k = random.randint(2, min(5, len(all_groups)))
                else:
                    k = random.randint(3, min(6, len(all_groups)))
                if len(all_groups) < k:
                    k = len(all_groups)
                
                picked = random.sample(all_groups, k)
                for g in picked:
                    v_code = str(g[0])[:12] + "00"
                    v_res = await session.execute(text("SELECT qsdwmc FROM qsdwdmb WHERE qsdwdm::text = :vc"), {"vc": v_code})
                    v_name = v_res.scalar() or v_code
                    sampled_groups.append({"code": g[0], "name": g[1], "v_name": v_name, "tz_name": tz_name})
            
            if not sampled_groups:
                return {"code": 400, "message": "所选乡镇下无村民组"}
        
        stats = []
        all_sampled_list = []
        groups_to_delete = []
        
        for g in sampled_groups:
            g_code = str(g["code"])
            tz_name = g.get("tz_name", req.township_name)
            
            # 查询该组当前已经在 waiye_samples 中的农户编码集合，严禁重复抽样该农户
            res_already = await session.execute(
                text("SELECT DISTINCT cbfbm FROM waiye_samples WHERE group_code = :gc"),
                {"gc": g_code}
            )
            already_sampled_cbfs = {str(r[0]) for r in res_already.fetchall() if r[0]}

            sql = text("SELECT cbfbm, cbfmc, lxdh FROM cbf WHERE cbfbm::text LIKE :code")
            res = await session.execute(sql, {"code": f"{g_code}%"})
            cbfs = res.fetchall()
            total_cbf = len(cbfs)
            
            if req.mode == 1:
                # Mode 1: 按村组手动抽样（支持增量补抽，绝不重复抽样已有农户，严禁删除历史外业记录）
                unselected_cbfs = [c for c in cbfs if str(c[0]) not in already_sampled_cbfs]
                if not unselected_cbfs:
                    return {
                        "code": 400,
                        "message": f"该村组所有承包方（共 {total_cbf} 户）已全部抽样，无法重复抽样！"
                    }
                
                # 计算待抽取数量
                if req.manual_sample_count is not None and req.manual_sample_count > 0:
                    needed_size = min(len(unselected_cbfs), req.manual_sample_count)
                else:
                    target_total = calc_sample_size(total_cbf, None)
                    current_count = len(already_sampled_cbfs)
                    needed_size = max(target_total - current_count, 1)
                    needed_size = min(needed_size, len(unselected_cbfs))

                sampled = random.sample(unselected_cbfs, needed_size)
                
                # Mode 1 不加入 groups_to_delete，严格保留已有外业记录
                final_sampled_count = len(already_sampled_cbfs) + len(sampled)
                stats.append({
                    "序号": len(stats) + 1,
                    "乡镇名称": tz_name,
                    "村名称": g["v_name"], 
                    "组名称": g["name"],
                    "发包方总户数": total_cbf,
                    "抽样农户数5%": final_sampled_count
                })
                for c in sampled:
                    all_sampled_list.append((tz_name, g["v_name"], g["name"], g_code, c))

            else:
                # Mode 2: 全镇随机重抽组
                sample_size = calc_sample_size(total_cbf, None)
                if sample_size > 0 and cbfs:
                    sampled = random.sample(cbfs, min(sample_size, len(cbfs)))
                    stats.append({
                        "序号": len(stats) + 1,
                        "乡镇名称": tz_name,
                        "村名称": g["v_name"], 
                        "组名称": g["name"],
                        "发包方总户数": total_cbf,
                        "抽样农户数5%": len(sampled)
                    })
                    groups_to_delete.append(g_code)
                    for c in sampled:
                        all_sampled_list.append((tz_name, g["v_name"], g["name"], g_code, c))

        if groups_to_delete:
            await session.execute(text("DELETE FROM waiye_samples WHERE group_code = ANY(:codes)"), {"codes": groups_to_delete})

        if all_sampled_list:
            all_cbfbms = [str(item[4][0]) for item in all_sampled_list if item[4][0]]
            cbf_parcels_map = defaultdict(list)
            if all_cbfbms:
                res_dks = await session.execute(text("""
                    SELECT b.cbfbm::text, b.dkbm::text, a.dkmc, b.htmjm 
                    FROM cbdkxx b
                    LEFT JOIN dkxx_shp_attrs a ON a.dkbm = b.dkbm
                    WHERE b.cbfbm = ANY(:cbfbms)
                """), {"cbfbms": all_cbfbms})
                for r_dk in res_dks.fetchall():
                    cbf_parcels_map[str(r_dk[0])].append(r_dk)

            insert_rows = []
            for tz_name, v_name, g_name, g_code, c in all_sampled_list:
                cbfbm_str = str(c[0]) if c[0] else ""
                cbfmc_str = c[1] or ""
                cbfbm_short_str = cbfbm_str[-4:] if cbfbm_str else ""
                lxdh_str = str(c[2]) if c[2] else ""
                dks = cbf_parcels_map.get(cbfbm_str, [])
                if not dks:
                    insert_rows.append({
                        "t_name": tz_name, "v_name": v_name, "g_name": g_name, "g_code": g_code,
                        "cbfmc": cbfmc_str, "cbfbm": cbfbm_str, "cbfbm_short": cbfbm_short_str, "lxdh": lxdh_str,
                        "dkmc": "", "dkbm": "", "dkbm_short": "", "scmj": 0.0
                    })
                else:
                    for dk in dks:
                        dkbm_str = str(dk[1]) if dk[1] else ""
                        insert_rows.append({
                            "t_name": tz_name, "v_name": v_name, "g_name": g_name, "g_code": g_code,
                            "cbfmc": cbfmc_str, "cbfbm": cbfbm_str, "cbfbm_short": cbfbm_short_str, "lxdh": lxdh_str,
                            "dkmc": dk[2] or "",
                            "dkbm": dkbm_str,
                            "dkbm_short": dkbm_str[-5:] if dkbm_str else "",
                            "scmj": float(dk[3]) if dk[3] is not None else 0.0
                        })

            if insert_rows:
                stmt = text("""
                    INSERT INTO waiye_samples (
                        township_name, village_name, group_name, group_code,
                        cbfmc, cbfbm, cbfbm_short, lxdh,
                        dkmc, dkbm, dkbm_short, scmj
                    ) VALUES (
                        :t_name, :v_name, :g_name, :g_code,
                        :cbfmc, :cbfbm, :cbfbm_short, :lxdh,
                        :dkmc, :dkbm, :dkbm_short, :scmj
                    )
                """)
                await session.execute(stmt, insert_rows)
                        
        await session.commit()
        # 由于支持了多乡镇，生成附件5时优先使用传入的首个代码/名称（保持向后兼容，但附件5内部展示可能会按真实名称展示）
        main_tz_code = req.township_codes[0] if req.township_codes else req.township_code
        main_tz_name = req.township_names[0] if req.township_names else req.township_name
        url_att5 = await asyncio.to_thread(export_att5, stats, main_tz_code, main_tz_name)
        
        return {
            "code": 200, 
            "message": "抽样成功！抽样统计表已生成，抽样数据已保存至外业核查数据库。",
            "stats": stats,
            "urls": [url_att5]
        }

@app.get("/api/download")
async def download_file(file: str):
    import urllib.parse
    file = urllib.parse.unquote(file).strip()
    if not os.path.isabs(file):
        clean_rel = file.lstrip("/\\")
        backend_file = os.path.join(os.path.dirname(__file__), clean_rel)
        if os.path.exists(backend_file):
            file = backend_file
    if os.path.exists(file):
        from fastapi.responses import FileResponse
        return FileResponse(file, filename=os.path.basename(file))
    return {"code": 404, "message": "File not found"}

@app.get("/api/generate_att4")
async def generate_att4(township_name: str = "默认乡镇", township_code: str = ""):
    from database import SessionLocal, parse_qsdwdmb_hierarchy
    from sqlalchemy import text
    async with SessionLocal() as session:
        if township_code:
            code_prefix = township_code
        else:
            r = await session.execute(text("SELECT qsdwdm FROM qsdwdmb WHERE qsdwmc = :name"), {"name": township_name})
            found_code = r.scalar()
            if found_code:
                code_prefix = str(found_code)
            else:
                r_h = await session.execute(text("SELECT qsdwdm, qsdwmc FROM qsdwdmb ORDER BY qsdwdm"))
                county_info, _ = parse_qsdwdmb_hierarchy(r_h.fetchall())
                code_prefix = county_info.get("code", "341124")
        
        r_cbf = await session.execute(text("SELECT COUNT(*) FROM cbf WHERE cbfbm::text LIKE :prefix"), {"prefix": f"{code_prefix}%"})
        farmer_count = r_cbf.scalar() or 0
        
        r_area = await session.execute(text("SELECT SUM(htmjm) FROM cbdkxx WHERE cbfbm::text LIKE :prefix"), {"prefix": f"{code_prefix}%"})
        total_area = float(r_area.scalar() or 0.0)
        
    url = await asyncio.to_thread(export_att4, township_name, farmer_count, total_area)
    return {"code": 200, "url": url}

@app.post("/api/upload_appform")
async def upload_appform(
    township_name: str = Form(...),
    township_code: str = Form(""),
    file: UploadFile = File(...)
):
    os.makedirs("uploads/appforms", exist_ok=True)
    clean_ts = sanitize_filename(township_name)
    ext = file.filename.split('.')[-1]
    filename = f"{clean_ts}（{township_code}）_验收申请表.{ext}"
    file_path = os.path.join("uploads/appforms", filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"code": 200, "message": "上传成功", "url": f"/api/download?file=uploads/appforms/{filename}"}

def extract_excel_group_info(row: dict) -> tuple:
    """
    智能解析抽样表格中每一行的发包方编码、乡镇名、村名、组名：
    具备智能容错与列倒置识别机制（例如当用户表格中首列为发包方编码数字、第二列为乡镇名，但表头写反或顺序倒置时，自动纠正）。
    """
    raw_code = str(row.get("发包方编码", "")).strip()
    raw_town = str(row.get("乡镇名", "")).strip()

    if raw_code.endswith('.0'): raw_code = raw_code[:-2]
    if raw_town.endswith('.0'): raw_town = raw_town[:-2]

    # 检测是否发生列值倒置（编码列放了中文乡镇名，而乡镇列放了纯数字编码）
    if raw_town.isdigit() and len(raw_town) >= 6 and (not raw_code.isdigit() or len(raw_code) < 6):
        real_code = raw_town
        real_town = raw_code
    else:
        real_code = raw_code
        real_town = raw_town

    vill = str(row.get("村名", "")).strip() if pd.notna(row.get("村名")) else ""
    group = str(row.get("组名", "")).strip() if pd.notna(row.get("组名")) else ""
    return real_code, real_town, vill, group

@app.post("/api/sample_by_excel/check")
async def check_sample_by_excel(file: UploadFile = File(...)):
    """预检上传的 Excel 抽样表格中各发包方的指定抽样户数是否符合验收规范要求（纯内存解析，杜绝文件锁）"""
    try:
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        return {"code": 400, "message": f"无法解析Excel文件，请检查文件格式是否有效: {str(e)}"}
        
    required = ["发包方编码", "乡镇名", "村名", "组名"]
    for r in required:
        if r not in df.columns:
            return {"code": 400, "message": f"表格缺少必要表头列: 【{r}】"}
            
    async with SessionLocal() as session:
        inspected_items = []
        insufficient_list = []
        exceeded_list = []
        
        # 村级维度统计聚合器: (village_code_prefix, township_name, village_name) -> dict
        village_groups_map = defaultdict(lambda: {
            "planned_sample_count": 0,
            "groups": []
        })

        for idx, row in df.iterrows():
            g_code, g_town, g_vill, g_name = extract_excel_group_info(row)
            group_desc = f"【{g_town} {g_vill} {g_name}】"

            sample_count = None
            if "抽样农户数" in df.columns and pd.notna(row["抽样农户数"]):
                try:
                    val = float(row["抽样农户数"])
                    sample_count = int(val)
                except:
                    pass
            
            sql = text("SELECT COUNT(*) FROM cbf WHERE cbfbm::text LIKE :code")
            res = await session.execute(sql, {"code": f"{g_code}%"})
            total_cbf = res.scalar() or 0
            
            check_res = check_group_sample_compliance(total_cbf, sample_count, group_desc)
            effective_sample_size = calc_sample_size(total_cbf, sample_count)

            item_data = {
                "row_idx": idx + 1,
                "group_code": g_code,
                "township_name": g_town,
                "village_name": g_vill,
                "group_name": g_name,
                "group_desc": group_desc,
                "effective_sample_size": effective_sample_size,
                **check_res
            }
            inspected_items.append(item_data)
            
            if check_res["is_insufficient"]:
                insufficient_list.append(item_data)
            elif check_res["status"] == "exceeded":
                exceeded_list.append(item_data)

            # 聚合至村级统计
            v_code_prefix = g_code[:12] if len(g_code) >= 12 else g_code
            v_key = (v_code_prefix, g_town, g_vill)
            village_groups_map[v_key]["planned_sample_count"] += effective_sample_size
            village_groups_map[v_key]["groups"].append(g_name)

        # 核验每个行政村的累计计划抽样数是否达到该村总户数的 5%
        village_warnings = []
        for (v_prefix, t_name, v_name), v_stat in village_groups_map.items():
            res_v = await session.execute(text("SELECT COUNT(*) FROM cbf WHERE cbfbm::text LIKE :code"), {"code": f"{v_prefix}%"})
            total_village_cbf = res_v.scalar() or 0
            planned_cnt = v_stat["planned_sample_count"]
            if total_village_cbf > 0:
                required_5pct = math.ceil(total_village_cbf * 0.05)
                if planned_cnt < required_5pct:
                    shortage = required_5pct - planned_cnt
                    rate_pct = round((planned_cnt / total_village_cbf) * 100, 1)
                    village_warnings.append({
                        "village_code": v_prefix,
                        "township_name": t_name,
                        "village_name": v_name,
                        "village_desc": f"【{t_name} {v_name}】",
                        "total_village_cbf": total_village_cbf,
                        "sample_count": planned_cnt,
                        "rate_pct": rate_pct,
                        "required_5pct": required_5pct,
                        "shortage": shortage,
                        "summary_text": f"【{t_name} {v_name}】全村总户数 {total_village_cbf} 户，表格计划抽检 {planned_cnt} 户 ({rate_pct}%)，未达到全村总户数的 5%（规定至少需抽 {required_5pct} 户，尚缺 {shortage} 户）"
                    })
                
        return {
            "code": 200,
            "data": {
                "total_groups": len(inspected_items),
                "insufficient_count": len(insufficient_list),
                "exceeded_count": len(exceeded_list),
                "has_insufficient": len(insufficient_list) > 0,
                "insufficient_list": insufficient_list,
                "exceeded_list": exceeded_list,
                "has_village_warning": len(village_warnings) > 0,
                "village_warning_count": len(village_warnings),
                "village_warnings": village_warnings,
                "details": inspected_items
            }
        }

@app.post("/api/sample_by_excel")
async def do_sample_by_excel(file: UploadFile = File(...), strategy: str = Form("append")):
    # 1. 纯内存直接读取解析，彻底规避 Windows 文件独占锁 (Permission denied)
    try:
        content = await file.read()
        df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        return {"code": 400, "message": f"无法解析Excel文件: {str(e)}"}

    # 2. 异步唯一命名安全归档备份（带时间戳和随机散列，绝不覆盖锁定文件，失败亦不影响核心业务）
    try:
        os.makedirs("uploads/抽样表", exist_ok=True)
        name_root, name_ext = os.path.splitext(file.filename)
        clean_root = sanitize_filename(name_root)
        backup_filename = f"{clean_root}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}{name_ext}"
        backup_path = os.path.join("uploads/抽样表", backup_filename)
        with open(backup_path, "wb") as bf:
            bf.write(content)
    except Exception as save_err:
        print(f"抽样表格归档副本异常 (已忽略): {save_err}")
        
    required = ["发包方编码", "乡镇名", "村名", "组名"]
    for r in required:
        if r not in df.columns:
            return {"code": 400, "message": f"表格缺少表头: {r}"}
            
    async with SessionLocal() as session:
        # 1. 严格全表前置合规性核验：抽样数不够必须强制拦截
        insufficient_list = []
        rows_to_sample = []

        for idx, row in df.iterrows():
            g_code, g_town, g_vill, g_name = extract_excel_group_info(row)
            group_desc = f"【{g_town} {g_vill} {g_name}】"

            sample_count = None
            if "抽样农户数" in df.columns and pd.notna(row["抽样农户数"]):
                try:
                    sample_count = int(float(row["抽样农户数"]))
                except:
                    pass
            
            sql = text("SELECT cbfbm, cbfmc, lxdh FROM cbf WHERE cbfbm::text LIKE :code")
            res = await session.execute(sql, {"code": f"{g_code}%"})
            cbfs = res.fetchall()
            total_cbf = len(cbfs)
            
            check_res = check_group_sample_compliance(total_cbf, sample_count, group_desc)
            if check_res["is_insufficient"]:
                insufficient_list.append({
                    "group_desc": group_desc,
                    "summary_text": check_res["summary_text"],
                    "message": check_res["message"]
                })
            
            sample_size = calc_sample_size(total_cbf, sample_count)
            rows_to_sample.append({
                "g_code": g_code,
                "g_town": g_town,
                "g_vill": g_vill,
                "g_name": g_name,
                "cbfs": cbfs,
                "total_cbf": total_cbf,
                "sample_size": sample_size
            })

        # 若发现存在任何一个发包方抽样数不够，立即强制拦截并返回具体未达标发包方清单
        if insufficient_list:
            error_messages = [f"{i+1}. {item['summary_text']}" for i, item in enumerate(insufficient_list)]
            return {
                "code": 400,
                "message": f"表格中检测到 {len(insufficient_list)} 个发包方抽样数不达标，已被系统强制拦截！",
                "insufficient_list": [item["summary_text"] for item in insufficient_list],
                "error_details": "\n".join(error_messages)
            }

        # 2. 合规核验通过，开始执行抽样与写库 (根据 strategy 处理 append增量补抽 或 overwrite覆盖重抽)
        stats = []
        all_sampled_list = []
        groups_to_delete = []
        is_append_mode = (strategy == "append")

        # 获取首行真实乡镇名与代码
        first_code, first_town, _, _ = extract_excel_group_info(df.iloc[0]) if not df.empty else ("", "默认乡镇", "", "")
        township_name = first_town if first_town else "默认乡镇"
        township_code = first_code[:9] if first_code else "000"
        
        for item in rows_to_sample:
            g_code = item["g_code"]
            g_town = item["g_town"]
            g_vill = item["g_vill"]
            g_name = item["g_name"]
            cbfs = item["cbfs"]
            total_cbf = item["total_cbf"]
            sample_size = item["sample_size"]
            
            if is_append_mode:
                # 增量补抽模式：排除已抽农户，绝不覆盖已有外业记录与签名
                res_already = await session.execute(
                    text("SELECT DISTINCT cbfbm FROM waiye_samples WHERE group_code = :gc"),
                    {"gc": g_code}
                )
                already_sampled_cbfs = {str(r[0]) for r in res_already.fetchall() if r[0]}
                unselected_cbfs = [c for c in cbfs if str(c[0]) not in already_sampled_cbfs]
                
                needed_count = max(sample_size - len(already_sampled_cbfs), 0)
                sampled = []
                if needed_count > 0 and unselected_cbfs:
                    sampled = random.sample(unselected_cbfs, min(needed_count, len(unselected_cbfs)))
                
                final_count = len(already_sampled_cbfs) + len(sampled)
                stats.append({
                    "序号": len(stats) + 1,
                    "乡镇名称": g_town,
                    "村名称": g_vill, 
                    "组名称": g_name,
                    "发包方总户数": total_cbf,
                    "抽样农户数5%": final_count
                })
                for c in sampled:
                    all_sampled_list.append((g_town, g_vill, g_name, g_code, c))
            else:
                # 覆盖重抽模式：删除表格涉及组的既有抽样，全量重新抽取
                if sample_size > 0 and cbfs:
                    sampled = random.sample(cbfs, min(sample_size, len(cbfs)))
                    stats.append({
                        "序号": len(stats) + 1,
                        "乡镇名称": g_town,
                        "村名称": g_vill, 
                        "组名称": g_name,
                        "发包方总户数": total_cbf,
                        "抽样农户数5%": len(sampled)
                    })
                    groups_to_delete.append(g_code)
                    for c in sampled:
                        all_sampled_list.append((g_town, g_vill, g_name, g_code, c))

        if groups_to_delete:
            await session.execute(text("DELETE FROM waiye_samples WHERE group_code = ANY(:codes)"), {"codes": groups_to_delete})

        if all_sampled_list:
            all_cbfbms = [str(item[4][0]) for item in all_sampled_list if item[4][0]]
            cbf_parcels_map = defaultdict(list)
            if all_cbfbms:
                res_dks = await session.execute(text("""
                    SELECT b.cbfbm::text, b.dkbm::text, a.dkmc, b.htmjm 
                    FROM cbdkxx b
                    LEFT JOIN dkxx_shp_attrs a ON a.dkbm = b.dkbm
                    WHERE b.cbfbm = ANY(:cbfbms)
                """), {"cbfbms": all_cbfbms})
                for r_dk in res_dks.fetchall():
                    cbf_parcels_map[str(r_dk[0])].append(r_dk)

            insert_rows = []
            for g_town, g_vill, g_name, g_code, c in all_sampled_list:
                cbfbm_str = str(c[0]) if c[0] else ""
                cbfmc_str = c[1] or ""
                cbfbm_short_str = cbfbm_str[-4:] if cbfbm_str else ""
                lxdh_str = str(c[2]) if c[2] else ""
                dks = cbf_parcels_map.get(cbfbm_str, [])
                if not dks:
                    insert_rows.append({
                        "t_name": g_town, "v_name": g_vill, "g_name": g_name, "g_code": g_code,
                        "cbfmc": cbfmc_str, "cbfbm": cbfbm_str, "cbfbm_short": cbfbm_short_str, "lxdh": lxdh_str,
                        "dkmc": "", "dkbm": "", "dkbm_short": "", "scmj": 0.0
                    })
                else:
                    for dk in dks:
                        dkbm_str = str(dk[1]) if dk[1] else ""
                        insert_rows.append({
                            "t_name": g_town, "v_name": g_vill, "g_name": g_name, "g_code": g_code,
                            "cbfmc": cbfmc_str, "cbfbm": cbfbm_str, "cbfbm_short": cbfbm_short_str, "lxdh": lxdh_str,
                            "dkmc": dk[2] or "",
                            "dkbm": dkbm_str,
                            "dkbm_short": dkbm_str[-5:] if dkbm_str else "",
                            "scmj": float(dk[3]) if dk[3] is not None else 0.0
                        })

            if insert_rows:
                stmt = text("""
                    INSERT INTO waiye_samples (
                        township_name, village_name, group_name, group_code,
                        cbfmc, cbfbm, cbfbm_short, lxdh,
                        dkmc, dkbm, dkbm_short, scmj
                    ) VALUES (
                        :t_name, :v_name, :g_name, :g_code,
                        :cbfmc, :cbfbm, :cbfbm_short, :lxdh,
                        :dkmc, :dkbm, :dkbm_short, :scmj
                    )
                """)
                await session.execute(stmt, insert_rows)
        
        await session.commit()
        url_att5 = await asyncio.to_thread(export_att5, stats, township_code, township_name)
        
        # 统计该批次涉及的各村最终抽查率是否达到 5%
        village_warnings = []
        v_stat_map = defaultdict(int)
        for s in stats:
            v_stat_map[(s["乡镇名称"], s["村名称"])] += s["抽样农户数5%"]

        for (t_name, v_name), v_total_sample in v_stat_map.items():
            res_v = await session.execute(text("""
                SELECT COUNT(*) FROM cbf WHERE cbfbm::text LIKE (
                    SELECT SUBSTRING(group_code, 1, 12) || '%' FROM waiye_samples WHERE township_name = :tn AND village_name = :vn LIMIT 1
                )
            """), {"tn": t_name, "vn": v_name})
            total_village_cbf = res_v.scalar() or 0
            if total_village_cbf > 0:
                required_5pct = math.ceil(total_village_cbf * 0.05)
                if v_total_sample < required_5pct:
                    shortage = required_5pct - v_total_sample
                    rate_pct = round((v_total_sample / total_village_cbf) * 100, 1)
                    village_warnings.append(f"【{t_name} {v_name}】全村总户数 {total_village_cbf} 户，累计抽检 {v_total_sample} 户 ({rate_pct}%)，未达到该村总户数的 5%（建议补抽 {shortage} 户）")

        return {
            "code": 200, 
            "message": "抽样成功！抽样统计表已生成，抽样数据已保存至外业核查数据库。",
            "stats": stats,
            "urls": [url_att5],
            "village_warnings": village_warnings
        }



class SampleClearRequest(BaseModel):
    township_code: Optional[str] = None
    township_name: Optional[str] = None
    group_code: Optional[str] = None
    level: Optional[str] = None

@app.post("/api/sample/clear")
async def clear_samples(req: Optional[SampleClearRequest] = None):
    async with SessionLocal() as session:
        if req and req.level == 'county':
            sql = text("DELETE FROM waiye_samples")
            await session.execute(sql)
            msg = "全县抽样数据已成功清空"
        elif req and req.group_code:
            sql = text("DELETE FROM waiye_samples WHERE group_code = :gc")
            await session.execute(sql, {"gc": req.group_code})
            msg = "指定村民组抽样数据已成功清空"
        elif req and (req.township_name or req.township_code):
            conds = []
            params = {}
            if req.township_name:
                conds.append("(township_name = :tn OR township_name LIKE :tn_like)")
                params["tn"] = req.township_name
                params["tn_like"] = f"%{req.township_name}%"
            if req.township_code:
                conds.append("group_code LIKE :tc")
                params["tc"] = f"{req.township_code}%"
            sql = text(f"DELETE FROM waiye_samples WHERE {' OR '.join(conds)}")
            await session.execute(sql, params)
            target = req.township_name or "该乡镇"
            msg = f"{target} 抽样数据已成功清空"
        else:
            sql = text("DELETE FROM waiye_samples")
            await session.execute(sql)
            msg = "全县抽样数据已成功清空"
            
        await session.commit()
        return {"code": 200, "message": msg}

@app.get("/api/sample/group_contractors")
async def get_sample_group_contractors(group_code: str):
    """
    获取指定发包方（村民小组）下已抽样的承包方列表
    """
    clean_code = str(group_code or "").strip()
    if not clean_code:
        return {"code": 400, "message": "发包方编码不能为空"}
    
    async with SessionLocal() as session:
        sql = text("""
            SELECT DISTINCT cbfbm, cbfmc, cbfbm_short, township_name, village_name, group_name
            FROM waiye_samples
            WHERE group_code = :gc
            ORDER BY cbfbm
        """)
        res = await session.execute(sql, {"gc": clean_code})
        rows = res.fetchall()
        data = []
        for r in rows:
            cbfbm_str = str(r[0]) if r[0] else ""
            cbfbm_short_str = str(r[2]) if r[2] else (cbfbm_str[-4:] if cbfbm_str else "")
            data.append({
                "cbfbm": cbfbm_str,
                "cbfmc": r[1] or "",
                "cbfbm_short": cbfbm_short_str,
                "township_name": r[3] or "",
                "village_name": r[4] or "",
                "group_name": r[5] or ""
            })
        return {"code": 200, "data": data, "total": len(data)}

class SampleDeleteContractorRequest(BaseModel):
    group_code: str
    cbfbm: str

@app.post("/api/sample/delete_contractor")
async def delete_sample_contractor(req: SampleDeleteContractorRequest, request: Request = None):
    """
    删除抽样数据中指定小组下的指定农户（仅从 waiye_samples 中删除，绝不更新主表 cbf）
    """
    clean_gc = str(req.group_code or "").strip()
    clean_cbfbm = str(req.cbfbm or "").strip()
    if not clean_gc or not clean_cbfbm:
        return {"code": 400, "message": "发包方编码和承包方编码均不能为空"}

    async with SessionLocal() as session:
        # 查询该农户信息以便审计
        r_info = await session.execute(
            text("SELECT cbfmc, township_name, village_name, group_name FROM waiye_samples WHERE group_code = :gc AND cbfbm = :cbfbm LIMIT 1"),
            {"gc": clean_gc, "cbfbm": clean_cbfbm}
        )
        row = r_info.fetchone()
        if not row:
            return {"code": 404, "message": "未在抽样数据中找到该农户记录"}
        
        cbfmc = row[0] or clean_cbfbm
        target_str = f"{row[1]} {row[2]} {row[3]} ({cbfmc})"

        # 1. 从外业抽样表中彻底删除该农户名下的所有地块抽样记录
        res_del = await session.execute(
            text("DELETE FROM waiye_samples WHERE group_code = :gc AND cbfbm = :cbfbm"),
            {"gc": clean_gc, "cbfbm": clean_cbfbm}
        )
        del_count = res_del.rowcount

        # 2. 同步清理可能的询问笔录记录
        await session.execute(
            text("DELETE FROM waiye_inquiries WHERE cbfbm = :cbfbm"),
            {"cbfbm": clean_cbfbm}
        )

        await session.commit()

        # 3. 审计日志
        record_check_audit(
            module_type="抽样管理",
            action_type="删除指定抽样农户",
            target_desc=target_str,
            details=f"从村民小组 (编码: {clean_gc}) 中剔除抽样农户 [{cbfmc}] (编码: {clean_cbfbm})，共移除 {del_count} 宗抽样地块",
            request=request
        )

        return {"code": 200, "message": f"农户【{cbfmc}】已成功从当前抽样中移除！", "deleted_parcels": del_count}

# ================= 内业核查 API =================

class NeiyeSaveRequest(BaseModel):
    qsdwdm: str
    qsdwmc: str
    level: str
    form_data: dict
    score: float

@app.post("/api/save_neiye")
async def save_neiye(req: NeiyeSaveRequest, request: Request = None):
    try:
        async with SessionLocal() as session:
            sql = text('''
                INSERT INTO neiye_records (qsdwdm, qsdwmc, level, form_data, score, updated_at)
                VALUES (:qsdwdm, :qsdwmc, :level, :form_data, :score, CURRENT_TIMESTAMP)
                ON CONFLICT (qsdwdm) DO UPDATE SET
                    qsdwmc = EXCLUDED.qsdwmc,
                    level = EXCLUDED.level,
                    form_data = EXCLUDED.form_data,
                    score = EXCLUDED.score,
                    updated_at = CURRENT_TIMESTAMP
            ''')
            await session.execute(sql, {
                "qsdwdm": req.qsdwdm,
                "qsdwmc": req.qsdwmc,
                "level": req.level,
                "form_data": json.dumps(req.form_data),
                "score": req.score
            })
            await session.commit()
            
            # 记录内业保存审计日志
            jcz = req.form_data.get("jcz_name", "")
            fhz = req.form_data.get("fhz_name", "")
            checker_info = f"检查者:{jcz} 复核者:{fhz}" if (jcz or fhz) else ""
            audit_detail = f"保存分值: {req.score}分 (层级: {req.level}) {checker_info}".strip()
            record_check_audit(
                module_type="内业核查",
                action_type="保存内业评分",
                target_desc=f"{req.qsdwmc} ({req.qsdwdm})",
                details=audit_detail,
                request=request
            )
            
            return {"code": 200, "message": "保存成功"}
    except Exception as e:
        print(f"save_neiye error: {e}")
        return {"code": 500, "message": f"保存内业记录失败: {str(e)}"}

@app.get("/api/get_neiye")
async def get_neiye(qsdwdm: str):
    async with SessionLocal() as session:
        sql = text("SELECT form_data, score FROM neiye_records WHERE qsdwdm = :qsdwdm")
        res = await session.execute(sql, {"qsdwdm": qsdwdm})
        row = res.fetchone()
        if row:
            return {"code": 200, "data": {"form_data": row[0], "score": row[1]}}
        return {"code": 404, "message": "No record"}

class ExportNeiyeAtt6Request(BaseModel):
    qsdwdm: str
    qsdwmc: str
    level: str
    township_name: Optional[str] = None
    village_name: Optional[str] = None
    form_data: Optional[dict] = None

@app.post("/api/export_neiye_att6")
async def api_export_neiye_att6(req: ExportNeiyeAtt6Request, request: Request = None):
    try:
        form_data = req.form_data
        if not form_data:
            async with SessionLocal() as session:
                sql = text("SELECT form_data FROM neiye_records WHERE qsdwdm = :qsdwdm")
                res = await session.execute(sql, {"qsdwdm": req.qsdwdm})
                row = res.fetchone()
                form_data = row[0] if row else {}
                
        if req.level == 'county':
            url = await asyncio.to_thread(export_neiye_att6_county, form_data)
        elif req.level == 'township':
            # 乡镇级内业核查：同县级，仅导出机制运行 1/4，书签严格映射为 XX县XX镇
            url = await asyncio.to_thread(
                export_neiye_att6_mechanism_only,
                form_data,
                is_county=False,
                township_name=req.township_name or req.qsdwmc
            )
        else:
            url = await asyncio.to_thread(
                export_neiye_att6_township, 
                req.qsdwmc, 
                form_data, 
                req.township_name, 
                req.village_name
            )
            
        record_check_audit(
            module_type="内业核查",
            action_type="导出附件6检查记录表",
            target_desc=f"{req.qsdwmc} ({req.level})",
            details=f"生成文档: {url.split('file=')[-1]}",
            request=request
        )
        return {"code": 200, "url": url}
    except Exception as e:
        print(f"api_export_neiye_att6 error: {e}")
        return {"code": 500, "message": f"生成附件6失败: {str(e)}"}

@app.get("/api/export_neiye_att7")
async def api_export_neiye_att7(request: Request = None):
    async with SessionLocal() as session:
        sql = text("SELECT qsdwdm, form_data, score FROM neiye_records")
        res = await session.execute(sql)
        rows = res.fetchall()
        records_dict = {}
        for r in rows:
            records_dict[str(r[0])] = {
                "form_data": r[1] if r[1] else {},
                "score": float(r[2]) if r[2] is not None else 0.0
            }
        
        # 构建乡镇 -> 其下抽样村代码列表的映射
        res_sampled_v = await session.execute(text("""
            SELECT DISTINCT 
                w.township_name, 
                SUBSTRING(w.group_code, 1, 12) || '00' as village_code
            FROM waiye_samples w
            WHERE w.village_name IS NOT NULL AND w.village_name != ''
        """))
        ts_v_map = defaultdict(list)
        for r in res_sampled_v.fetchall():
            ts_v_map[r[0]].append(str(r[1]))
        
    url = await asyncio.to_thread(export_neiye_att7, records_dict, dict(ts_v_map))
    record_check_audit(
        module_type="内业核查",
        action_type="导出附件7内业检查得分表",
        target_desc="全县内业得分汇总",
        details=f"生成文档: {url.split('file=')[-1]}",
        request=request
    )
    return {"code": 200, "url": url}

# ================= 外业核查 API =================

@app.get("/api/waiye/hierarchy")
async def get_waiye_hierarchy():
    async with SessionLocal() as session:
        sql = text("""
            SELECT township_name, village_name, group_name, group_code, 
                   COUNT(DISTINCT cbfbm) as cbf_count,
                   COUNT(NULLIF(dkbm, '')) as dk_count
            FROM waiye_samples
            GROUP BY township_name, village_name, group_name, group_code
            ORDER BY township_name, village_name, group_name
        """)
        res = await session.execute(sql)
        rows = res.fetchall()
        
        township_map = {}
        for r in rows:
            t_name, v_name, g_name, g_code, cbf_cnt, dk_cnt = r[0], r[1], r[2], r[3], r[4], r[5]
            if t_name not in township_map:
                township_map[t_name] = {}
            if v_name not in township_map[t_name]:
                township_map[t_name][v_name] = []
            township_map[t_name][v_name].append({
                "name": g_name,
                "code": g_code,
                "cbf_count": cbf_cnt,
                "dk_count": dk_cnt
            })
            
        tree = []
        for t_name, v_dict in township_map.items():
            v_children = []
            for v_name, g_list in v_dict.items():
                # 提取村级真实 14 位区划代码 (组编码前 12 位 + '00')
                first_gcode = str(g_list[0]["code"]) if g_list else ""
                v_code = (first_gcode[:12] + "00") if len(first_gcode) >= 12 else v_name

                g_children = [
                    {
                        "text": f"{g['name']} ({g['cbf_count']}户/{g['dk_count']}地块)",
                        "value": g["code"],
                        "group_name": g["name"],
                        "group_code": g["code"],
                        "village_name": v_name,
                        "village_code": v_code,
                        "township_name": t_name,
                        "cbf_count": g["cbf_count"],
                        "dk_count": g["dk_count"]
                    }
                    for g in g_list
                ]
                v_children.append({
                    "text": v_name,
                    "value": v_code,
                    "village_code": v_code,
                    "village_name": v_name,
                    "township_name": t_name,
                    "children": g_children
                })
            tree.append({
                "text": t_name,
                "value": t_name,
                "township_name": t_name,
                "children": v_children
            })
            
        return {"code": 200, "tree": tree, "total_groups": len(rows)}

@app.get("/api/waiye/group_samples")
async def get_waiye_group_samples(
    group_code: Optional[str] = None,
    township_name: Optional[str] = None,
    village_name: Optional[str] = None,
    group_name: Optional[str] = None
):
    async with SessionLocal() as session:
        if group_code:
            sql = text("""
                SELECT id, township_name, village_name, group_name, group_code,
                       cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method, signature_url, phone_correct
                FROM waiye_samples
                WHERE group_code = :gc
                ORDER BY id
            """)
            res = await session.execute(sql, {"gc": group_code})
        else:
            sql = text("""
                SELECT id, township_name, village_name, group_name, group_code,
                       cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method, signature_url, phone_correct
                FROM waiye_samples
                WHERE township_name = :tn AND village_name = :vn AND group_name = :gn
                ORDER BY id
            """)
            res = await session.execute(sql, {"tn": township_name, "vn": village_name, "gn": group_name})
            
        rows = res.fetchall()
        data = []
        sig_dir = os.path.join("uploads", "signatures")
        
        for r in rows:
            cbfbm_val = str(r[6]) if r[6] else ""
            sig_file = os.path.join(sig_dir, f"{cbfbm_val}.png")
            sig_url = ""
            if os.path.exists(sig_file):
                mtime = int(os.path.getmtime(sig_file))
                sig_url = f"/api/signature_image?cbfbm={cbfbm_val}&v={mtime}"
            elif r[21]:
                sig_url = r[21]
                
            data.append({
                "id": r[0],
                "township_name": r[1],
                "village_name": r[2],
                "group_name": r[3],
                "group_code": r[4],
                "cbfmc": r[5],
                "cbfbm": cbfbm_val,
                "cbfbm_short": r[7],
                "lxdh": r[8],
                "dkmc": r[9],
                "dkbm": r[10],
                "dkbm_short": r[11],
                "scmj": float(r[12]) if r[12] is not None else 0.0,
                "area_acknowledged": r[13] or "",
                "rights_correct": r[14] or "",
                "bound_correct": r[15] or "",
                "member_qualified": r[16] or "",
                "self_verified": r[17] or "",
                "self_signed": r[18] or "",
                "satisfaction": r[19] or "满意",
                "survey_method": r[20] or "现场",
                "signature_url": sig_url,
                "phone_correct": r[22] or ""
            })
            
        return {"code": 200, "data": data}

class SignatureSaveRequest(BaseModel):
    cbfbm: str
    cbfmc: str
    signature_data: str

@app.post("/api/waiye/save_signature")
async def save_waiye_signature(req: SignatureSaveRequest, request: Request = None):
    os.makedirs(os.path.join("uploads", "signatures"), exist_ok=True)
    raw_b64 = req.signature_data
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]
    
    img_bytes = base64.b64decode(raw_b64)
    file_path = os.path.join("uploads", "signatures", f"{req.cbfbm}.png")
    with open(file_path, "wb") as f:
        f.write(img_bytes)
        
    mtime = int(os.path.getmtime(file_path))
    sig_url = f"/api/signature_image?cbfbm={req.cbfbm}&v={mtime}"
    
    async with SessionLocal() as session:
        # 1. Update/insert contractor_signatures
        await session.execute(text("""
            INSERT INTO contractor_signatures (cbfbm, cbfmc, signature_path, signature_data, updated_at)
            VALUES (:cbfbm, :cbfmc, :sig_path, :sig_data, CURRENT_TIMESTAMP)
            ON CONFLICT (cbfbm) DO UPDATE SET
                cbfmc = EXCLUDED.cbfmc,
                signature_path = EXCLUDED.signature_path,
                signature_data = EXCLUDED.signature_data,
                updated_at = CURRENT_TIMESTAMP
        """), {
            "cbfbm": req.cbfbm,
            "cbfmc": req.cbfmc,
            "sig_path": file_path,
            "sig_data": req.signature_data[:500] # store preview or header
        })
        
        # 2. Update all waiye_samples with this cbfbm
        await session.execute(text("""
            UPDATE waiye_samples 
            SET signature_url = :sig_url, updated_at = CURRENT_TIMESTAMP
            WHERE cbfbm = :cbfbm
        """), {
            "sig_url": sig_url,
            "cbfbm": req.cbfbm
        })
        await session.commit()

    record_check_audit(
        module_type="外业核查",
        action_type="承包方代表手写签名",
        target_desc=f"{req.cbfmc} ({req.cbfbm})",
        details=f"电子签名文件: {req.cbfbm}.png 已保存并关联对应地块",
        request=request
    )
        
    return {
        "code": 200,
        "message": f"【{req.cbfmc}】代表手写签名已保存并关联！",
        "signature_url": sig_url,
        "cbfbm": req.cbfbm
    }

@app.get("/api/signature_image")
async def get_signature_image(cbfbm: str):
    file_path = os.path.join("uploads", "signatures", f"{cbfbm}.png")
    if os.path.exists(file_path):
        from fastapi.responses import FileResponse
        return FileResponse(file_path, media_type="image/png")
    return Response(status_code=404)


class WaiyeRecordItem(BaseModel):
    id: int
    area_acknowledged: Optional[str] = ""
    rights_correct: Optional[str] = ""
    bound_correct: Optional[str] = ""
    member_qualified: Optional[str] = ""
    self_verified: Optional[str] = ""
    self_signed: Optional[str] = ""
    satisfaction: Optional[str] = "满意"
    survey_method: Optional[str] = "现场"
    phone_correct: Optional[str] = ""

class WaiyeSaveRequest(BaseModel):
    records: List[WaiyeRecordItem]

@app.post("/api/waiye/save_records")
async def save_waiye_records(req: WaiyeSaveRequest, request: Request = None):
    async with SessionLocal() as session:
        sql = text("""
            UPDATE waiye_samples SET
                area_acknowledged = :area_ack,
                rights_correct = :rights_cor,
                bound_correct = :bound_cor,
                member_qualified = :member_qual,
                self_verified = :self_ver,
                self_signed = :self_sig,
                satisfaction = :sat,
                survey_method = :sm,
                phone_correct = :phone_cor,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = :id
        """)
        for item in req.records:
            await session.execute(sql, {
                "id": item.id,
                "area_ack": item.area_acknowledged or "",
                "rights_cor": item.rights_correct or "",
                "bound_cor": item.bound_correct or "",
                "member_qual": item.member_qualified or "",
                "self_ver": item.self_verified or "",
                "self_sig": item.self_signed or "",
                "sat": item.satisfaction or "满意",
                "sm": item.survey_method or "现场",
                "phone_cor": item.phone_correct or ""
            })
        await session.commit()
        
        # 获取首条样本的组别信息以便审计展示
        if req.records:
            first_id = req.records[0].id
            r_info = await session.execute(text("SELECT township_name, village_name, group_name FROM waiye_samples WHERE id = :id"), {"id": first_id})
            row_inf = r_info.fetchone()
            target_str = f"{row_inf[0]} {row_inf[1]} {row_inf[2]}" if row_inf else f"记录ID: {first_id}"
            record_check_audit(
                module_type="外业核查",
                action_type="保存外业地块核查状态",
                target_desc=target_str,
                details=f"批量更新了 {len(req.records)} 宗地块的核查指标（权属、四至、成员、满意度）",
                request=request
            )

        return {"code": 200, "message": "保存成功"}

class WaiyePhoneUpdateRequest(BaseModel):
    cbfbm: str
    lxdh: str

@app.post("/api/waiye/update_phone")
async def api_update_waiye_phone(req: WaiyePhoneUpdateRequest, request: Request = None):
    """
    仅更新外业抽样核查表 waiye_samples 中的农户联系电话，严禁修改原始主表 cbf
    """
    clean_cbfbm = str(req.cbfbm or "").strip()
    clean_lxdh = str(req.lxdh or "").strip()
    if not clean_cbfbm:
        return {"code": 400, "message": "承包方编码不能为空"}

    async with SessionLocal() as session:
        # 查询该承包方在 waiye_samples 中的信息以便审计
        r_info = await session.execute(
            text("SELECT cbfmc, township_name, village_name, group_name FROM waiye_samples WHERE cbfbm = :cbfbm LIMIT 1"),
            {"cbfbm": clean_cbfbm}
        )
        row = r_info.fetchone()
        cbfmc = row[0] if row else clean_cbfbm
        target_str = f"{row[1]} {row[2]} {row[3]} ({cbfmc})" if row else clean_cbfbm

        # 仅更新 waiye_samples 表，绝不触碰 cbf
        res = await session.execute(
            text("""
                UPDATE waiye_samples 
                SET lxdh = :lxdh, updated_at = CURRENT_TIMESTAMP 
                WHERE cbfbm = :cbfbm
            """),
            {"cbfbm": clean_cbfbm, "lxdh": clean_lxdh}
        )
        await session.commit()

        # 审计日志
        record_check_audit(
            module_type="外业核查",
            action_type="外业补录联系电话",
            target_desc=target_str,
            details=f"承包方 [{cbfmc}] (编码: {clean_cbfbm}) 联系电话更新为: {clean_lxdh or '（空）'}",
            request=request
        )

        return {"code": 200, "message": "电话更新成功", "lxdh": clean_lxdh, "updated_count": res.rowcount}

class ExportWaiyeAtt8Request(BaseModel):
    township_name: str
    village_name: Optional[str] = None
    group_name: Optional[str] = None
    group_code: Optional[str] = None

@app.post("/api/export_waiye_att8")
async def api_export_waiye_att8(req: ExportWaiyeAtt8Request, request: Request = None):
    async with SessionLocal() as session:
        if req.group_code:
            sql = text("""
                SELECT id, township_name, village_name, group_name,
                       cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method, signature_url, phone_correct
                FROM waiye_samples
                WHERE group_code = :gc
                ORDER BY cbfbm, id
            """)
            res = await session.execute(sql, {"gc": req.group_code})
        elif req.village_name and req.group_name:
            sql = text("""
                SELECT id, township_name, village_name, group_name,
                       cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method, signature_url, phone_correct
                FROM waiye_samples
                WHERE township_name = :tn AND village_name = :vn AND group_name = :gn
                ORDER BY cbfbm, id
            """)
            res = await session.execute(sql, {"tn": req.township_name, "vn": req.village_name, "gn": req.group_name})
        else:
            sql = text("""
                SELECT id, township_name, village_name, group_name,
                       cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method, signature_url, phone_correct
                FROM waiye_samples
                WHERE township_name = :tn
                ORDER BY village_name, group_name, cbfbm, id
            """)
            res = await session.execute(sql, {"tn": req.township_name})
            
        rows = res.fetchall()
        if not rows:
            return {"code": 404, "message": "未查询到该范围的抽样记录"}
            
        from collections import defaultdict
        groups_map = defaultdict(list)
        for r in rows:
            key = (r[1], r[2], r[3])
            groups_map[key].append({
                "id": r[0],
                "township_name": r[1],
                "village_name": r[2],
                "group_name": r[3],
                "cbfmc": r[4],
                "cbfbm": str(r[5]) if r[5] else "",
                "cbfbm_short": r[6],
                "lxdh": r[7],
                "dkmc": r[8],
                "dkbm_short": r[9],
                "scmj": float(r[10]) if r[10] is not None else 0.0,
                "area_acknowledged": r[11] or "",
                "rights_correct": r[12] or "",
                "bound_correct": r[13] or "",
                "member_qualified": r[14] or "",
                "self_verified": r[15] or "",
                "self_signed": r[16] or "",
                "satisfaction": r[17] or "满意",
                "survey_method": r[18] or "现场",
                "signature_url": r[19] or "",
                "phone_correct": r[20] or ""
            })
            
        urls = []
        for (t_name, v_name, g_name), g_rows in groups_map.items():
            url = await asyncio.to_thread(
                export_waiye_att8,
                t_name,
                v_name,
                g_name,
                g_rows
            )
            urls.append(url)

        scope_desc = f"{req.township_name} {req.village_name or ''} {req.group_name or ''}".strip()
        record_check_audit(
            module_type="外业核查",
            action_type="导出附件8外业核查记录表",
            target_desc=scope_desc,
            details=f"成功生成 {len(urls)} 份附件8文档",
            request=request
        )
            
        return {
            "code": 200, 
            "url": urls[0] if urls else "",
            "urls": urls,
            "count": len(urls),
            "message": f"已成功生成 {len(urls)} 份附件8文档！"
        }

@app.get("/api/export_waiye_att9")
async def api_export_waiye_att9(request: Request = None):
    from database import SessionLocal
    from sqlalchemy import text
    async with SessionLocal() as session:
        sql = text("""
            SELECT id, township_name, village_name, group_name,
                   cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm_short, scmj,
                   area_acknowledged, rights_correct, bound_correct, member_qualified,
                   self_verified, self_signed, satisfaction, survey_method, signature_url, phone_correct
            FROM waiye_samples
            ORDER BY township_name, village_name, group_name, cbfbm, id
        """)
        res = await session.execute(sql)
        rows = res.fetchall()
        if not rows:
            return {"code": 404, "message": "暂无外业抽样记录"}
            
        samples_rows = []
        for r in rows:
            samples_rows.append({
                "id": r[0],
                "township_name": r[1],
                "village_name": r[2],
                "group_name": r[3],
                "cbfmc": r[4],
                "cbfbm": str(r[5]) if r[5] else "",
                "cbfbm_short": r[6],
                "lxdh": r[7],
                "dkmc": r[8],
                "dkbm_short": r[9],
                "scmj": float(r[10]) if r[10] is not None else 0.0,
                "area_acknowledged": r[11] or "",
                "rights_correct": r[12] or "",
                "bound_correct": r[13] or "",
                "member_qualified": r[14] or "",
                "self_verified": r[15] or "",
                "self_signed": r[16] or "",
                "satisfaction": r[17] or "满意",
                "survey_method": r[18] or "现场",
                "signature_url": r[19] or "",
                "phone_correct": r[20] or ""
            })
            
    url = await asyncio.to_thread(export_waiye_att9, samples_rows)
    record_check_audit(
        module_type="外业核查",
        action_type="导出附件9外业检查得分表",
        target_desc="全县外业抽检汇总",
        details=f"生成文档: {url.split('file=')[-1]}",
        request=request
    )
    return {"code": 200, "url": url}

@app.get("/api/tasks/progress_dashboard")
async def get_tasks_progress_dashboard():
    from database import SessionLocal, parse_qsdwdmb_hierarchy, load_config
    from doc_exporter import calculate_neiye_subscores
    async with SessionLocal() as session:
        # 1. 查询县级信息与全部乡镇列表
        res_h = await session.execute(text("SELECT qsdwdm, qsdwmc FROM qsdwdmb ORDER BY qsdwdm"))
        county_info, all_townships = parse_qsdwdmb_hierarchy(res_h.fetchall())
        county_name = county_info.get("name", "全县")
        total_townships_count = len(all_townships)

        # 2. 查询各已抽样乡镇的外业总体情况（组数、农户数、地块数、签名数、核对数、错误项）
        res_wai = await session.execute(text("""
            SELECT township_name,
                   COUNT(DISTINCT group_code) as group_count,
                   COUNT(DISTINCT cbfbm) as farmer_count,
                   COUNT(*) as parcel_count,
                   COUNT(DISTINCT CASE WHEN signature_url IS NOT NULL AND signature_url != '' THEN cbfbm END) as signed_farmers,
                   COUNT(DISTINCT CASE WHEN area_acknowledged != '' OR rights_correct != '' OR bound_correct != '' OR member_qualified != '' OR self_verified != '' OR self_signed != '' THEN cbfbm END) as checked_farmers,
                   SUM(CASE WHEN area_acknowledged = 'X' THEN 1 ELSE 0 END +
                       CASE WHEN rights_correct = 'X' THEN 1 ELSE 0 END +
                       CASE WHEN bound_correct = 'X' THEN 1 ELSE 0 END +
                       CASE WHEN member_qualified = 'X' THEN 1 ELSE 0 END +
                       CASE WHEN self_verified = 'X' THEN 1 ELSE 0 END +
                       CASE WHEN self_signed = 'X' THEN 1 ELSE 0 END) as total_errors,
                   SUM(CASE WHEN satisfaction = '满意' THEN 1 ELSE 0 END) as sat_count
            FROM waiye_samples
            WHERE township_name IS NOT NULL AND township_name != ''
            GROUP BY township_name
            ORDER BY township_name
        """))
        wai_map = {}
        for r in res_wai.fetchall():
            wai_map[r[0]] = {
                "group_count": int(r[1]),
                "farmer_count": int(r[2]),
                "parcel_count": int(r[3]),
                "signed_farmers": int(r[4] or 0),
                "checked_farmers": int(r[5] or 0),
                "total_errors": int(r[6] or 0),
                "sat_count": int(r[7] or 0)
            }

        # 3. 查询每个乡镇下抽样的具体行政村列表
        res_v = await session.execute(text("""
            SELECT DISTINCT township_name, village_name, SUBSTRING(group_code, 1, 12) || '00' as village_code
            FROM waiye_samples
            WHERE village_name IS NOT NULL AND village_name != ''
            ORDER BY township_name, village_code
        """))
        town_villages = defaultdict(list)
        for r in res_v.fetchall():
            town_villages[r[0]].append({
                "village_name": r[1],
                "village_code": str(r[2])
            })

        # 4. 查询已保存的内业记录
        res_n = await session.execute(text("SELECT qsdwdm, qsdwmc, form_data, score FROM neiye_records"))
        neiye_records_map = {}
        for r in res_n.fetchall():
            code_str = str(r[0])
            score_val = float(r[3]) if r[3] is not None else None
            neiye_records_map[code_str] = {
                "qsdwmc": r[1],
                "form_data": r[2] or {},
                "score": score_val
            }

        # 5. 组织已抽样乡镇的卡片列表
        township_list = []
        total_groups_sum = 0
        total_farmers_sum = 0
        total_parcels_sum = 0
        total_villages_sum = 0
        completed_villages_sum = 0
        total_signed_farmers_sum = 0

        # 按区划代码顺序排列已抽样乡镇
        ordered_townships = [t["name"] for t in all_townships if t["name"] in wai_map]
        if not ordered_townships:
            ordered_townships = list(wai_map.keys())

        for t_name in ordered_townships:
            w_info = wai_map[t_name]
            v_list = town_villages.get(t_name, [])
            
            # 内业村级进度分析
            v_details = []
            v_scores = []
            for v_item in v_list:
                v_code = v_item["village_code"]
                has_done = (v_code in neiye_records_map)
                cur_sc = None
                if has_done:
                    nr = neiye_records_map[v_code]
                    if nr["score"] is not None:
                        cur_sc = nr["score"]
                    else:
                        sub = calculate_neiye_subscores(nr["form_data"])["score"]
                        cur_sc = sub.get("total", 0.0)
                    v_scores.append(cur_sc)

                v_details.append({
                    "village_name": v_item["village_name"],
                    "village_code": v_code,
                    "completed": has_done,
                    "score": cur_sc
                })

            total_v_cnt = len(v_list)
            done_v_cnt = len([v for v in v_details if v["completed"]])
            neiye_pct = round((done_v_cnt / total_v_cnt * 100), 1) if total_v_cnt > 0 else 0.0
            avg_neiye_score = round(sum(v_scores) / len(v_scores), 1) if v_scores else None

            # 外业进度分析
            total_f_cnt = w_info["farmer_count"]
            signed_f_cnt = w_info["signed_farmers"]
            checked_f_cnt = w_info["checked_farmers"]
            waiye_pct = round((signed_f_cnt / total_f_cnt * 100), 1) if total_f_cnt > 0 else 0.0
            
            err_cnt = w_info["total_errors"]
            sat_cnt = w_info["sat_count"]
            p_cnt = w_info["parcel_count"]
            prog_score = max(round(20.0 - err_cnt * 0.5, 1), 0.0)
            effect_score = round(sat_cnt / p_cnt * 10.0, 1) if p_cnt > 0 else 10.0

            # 综合状态判断
            if neiye_pct == 100.0 and (waiye_pct == 100.0 or checked_f_cnt >= total_f_cnt):
                status_code = "completed"
                status_text = "已完成"
            elif neiye_pct > 0 or waiye_pct > 0 or checked_f_cnt > 0:
                status_code = "in_progress"
                status_text = "进行中"
            else:
                status_code = "not_started"
                status_text = "待核查"

            # 累计全县总量
            total_groups_sum += w_info["group_count"]
            total_farmers_sum += total_f_cnt
            total_parcels_sum += p_cnt
            total_villages_sum += total_v_cnt
            completed_villages_sum += done_v_cnt
            total_signed_farmers_sum += signed_f_cnt

            township_list.append({
                "township_name": t_name,
                "group_count": w_info["group_count"],
                "farmer_count": total_f_cnt,
                "parcel_count": p_cnt,
                "status_code": status_code,
                "status_text": status_text,
                "neiye": {
                    "total_villages": total_v_cnt,
                    "completed_villages": done_v_cnt,
                    "percent": neiye_pct,
                    "avg_score": avg_neiye_score,
                    "village_details": v_details
                },
                "waiye": {
                    "total_farmers": total_f_cnt,
                    "signed_farmers": signed_f_cnt,
                    "checked_farmers": checked_f_cnt,
                    "percent": waiye_pct,
                    "prog_score": prog_score,
                    "effect_score": effect_score
                }
            })

        global_neiye_pct = round((completed_villages_sum / total_villages_sum * 100), 1) if total_villages_sum > 0 else 0.0
        global_waiye_pct = round((total_signed_farmers_sum / total_farmers_sum * 100), 1) if total_farmers_sum > 0 else 0.0

        return {
            "code": 200,
            "data": {
                "global_stats": {
                    "county_name": county_name,
                    "total_townships": total_townships_count,
                    "sampled_townships_count": len(township_list),
                    "sampled_groups_count": total_groups_sum,
                    "sampled_farmers_count": total_farmers_sum,
                    "sampled_parcels_count": total_parcels_sum,
                    "neiye_total_villages": total_villages_sum,
                    "neiye_completed_villages": completed_villages_sum,
                    "neiye_percent": global_neiye_pct,
                    "waiye_total_farmers": total_farmers_sum,
                    "waiye_signed_farmers": total_signed_farmers_sum,
                    "waiye_percent": global_waiye_pct,
                    "is_groups_compliant": total_groups_sum >= 20
                },
                "township_list": township_list
            }
        }

@app.get("/api/waiye/townships_summary")
async def get_waiye_townships_summary():
    from database import SessionLocal
    from sqlalchemy import text
    async with SessionLocal() as session:
        sql = text("""
            SELECT township_name, village_name, group_name, group_code,
                   COUNT(*) as parcel_count,
                   COUNT(DISTINCT cbfbm) as farmer_count,
                   SUM(CASE WHEN area_acknowledged = 'X' THEN 1 ELSE 0 END +
                       CASE WHEN rights_correct = 'X' THEN 1 ELSE 0 END +
                       CASE WHEN bound_correct = 'X' THEN 1 ELSE 0 END +
                       CASE WHEN member_qualified = 'X' THEN 1 ELSE 0 END +
                       CASE WHEN self_verified = 'X' THEN 1 ELSE 0 END +
                       CASE WHEN self_signed = 'X' THEN 1 ELSE 0 END) as error_count,
                   SUM(CASE WHEN satisfaction = '满意' THEN 1 ELSE 0 END) as sat_count
            FROM waiye_samples
            GROUP BY township_name, village_name, group_name, group_code
            ORDER BY township_name, village_name, group_name
        """)
        res = await session.execute(sql)
        rows = res.fetchall()
        
        township_map = {}
        for r in rows:
            t_name = r[0]
            if t_name not in township_map:
                township_map[t_name] = {"township_name": t_name, "groups": [], "total_parcels": 0, "total_errors": 0}
            
            p_cnt = int(r[4])
            err_cnt = int(r[6] or 0)
            sat_cnt = int(r[7] or 0)
            prog_score = max(20.0 - err_cnt * 0.5, 0.0)
            effect_score = (sat_cnt / p_cnt * 10.0) if p_cnt > 0 else 10.0
            
            township_map[t_name]["groups"].append({
                "village_name": r[1],
                "group_name": r[2],
                "group_code": r[3],
                "parcel_count": p_cnt,
                "farmer_count": int(r[5]),
                "error_count": err_cnt,
                "prog_score": prog_score,
                "effect_score": effect_score
            })
            township_map[t_name]["total_parcels"] += p_cnt
            township_map[t_name]["total_errors"] += err_cnt
            
        summary = list(township_map.values())
        return {"code": 200, "data": summary}


@app.get("/api/waiye/family_members")
async def get_family_members(cbfbm: str):
    from database import SessionLocal
    from sqlalchemy import text
    async with SessionLocal() as session:
        sql = text("SELECT cyxm, cyzjlx, cyzjhm, yhzgx, cyxb FROM cbf_jtcy WHERE cbfbm = :cbfbm")
        result = await session.execute(sql, {"cbfbm": cbfbm})
        rows = result.fetchall()
        data = [{"name": r[0], "id_type": r[1], "id_no": r[2], "relation": r[3], "gender": r[4]} for r in rows]
        return {"code": 200, "data": data}

@app.get("/api/waiye/parcel_bounds")
async def get_parcel_bounds(dkbm: str):
    from database import SessionLocal
    from sqlalchemy import text
    async with SessionLocal() as session:
        sql = text("SELECT dkdz, dkxz, dknz, dkbz FROM dkxx_shp_attrs WHERE dkbm = :dkbm")
        result = await session.execute(sql, {"dkbm": dkbm})
        row = result.fetchone()
        if row:
            data = {"east": row[0], "west": row[1], "south": row[2], "north": row[3]}
        else:
            data = {"east": "", "west": "", "south": "", "north": ""}
        return {"code": 200, "data": data}



from pydantic import BaseModel
class ExportAtt1011Request(BaseModel):
    special1: bool
    special2: bool
    special3: float
    
@app.get("/api/score/summary")
async def get_score_summary():
    from score_service import get_all_township_scores, calculate_county_averages
    async with SessionLocal() as session:
        scores, c_mech, has_c = await get_all_township_scores(session)
        
    county_avg = calculate_county_averages(scores, c_mech, has_c)
    return {
        "code": 200,
        "data": {
            "mech": county_avg["mech"],
            "prog_nei": county_avg["prog_nei"],
            "policy": county_avg["policy"],
            "effect_nei": county_avg["effect_nei"],
            "prog_wai": county_avg["prog_wai"],
            "effect_wai": county_avg["effect_wai"]
        }
    }

@app.get("/api/export_att10")
async def api_export_att10():
    from score_service import get_all_township_scores
    from doc_exporter_score import export_att10
    async with SessionLocal() as session:
        scores, c_mech, _ = await get_all_township_scores(session)
    url = await asyncio.to_thread(export_att10, scores, c_mech)
    return {"code": 200, "url": url}

@app.post("/api/export_att11")
async def api_export_att11(req: ExportAtt1011Request):
    from score_service import get_all_township_scores, calculate_county_averages
    from doc_exporter_score import export_att11
    async with SessionLocal() as session:
        scores, c_mech, has_c = await get_all_township_scores(session)
        
    county_avg = calculate_county_averages(scores, c_mech, has_c)
    deduct = (0.5 if req.special1 else 0.0) + (1.0 if req.special2 else 0.0) + req.special3
    final_score = county_avg["mech"] + county_avg["prog_nei"] + county_avg["policy"] + county_avg["effect_nei"] + county_avg["prog_wai"] + county_avg["effect_wai"] - deduct
    final_score = max(round(final_score, 1), 0.0)
    
    url = await asyncio.to_thread(export_att11, county_avg, req.special1, req.special2, req.special3, final_score)
    return {"code": 200, "url": url}

# ================= 自查整改（附件12 / 附件13） =================

class ExportSampleDetailExcelRequest(BaseModel):
    township_name: str

@app.post("/api/export_sample_detail_excel")
async def api_export_sample_detail_excel(req: ExportSampleDetailExcelRequest, request: Request = None):
    """单独导出指定乡镇自查抽样农户明细表 Excel (.xlsx)"""
    async with SessionLocal() as session:
        r_cbf_detail = await session.execute(text("""
            SELECT DISTINCT
                w.township_name,
                w.village_name,
                w.group_name,
                w.cbfbm,
                w.cbfmc,
                COALESCE(c.cbfzjhm, '') as cbfzjhm
            FROM waiye_samples w
            LEFT JOIN cbf c ON w.cbfbm::text = c.cbfbm::text
            WHERE w.township_name = :name
            ORDER BY w.village_name, w.group_name, w.cbfbm
        """), {"name": req.township_name})
        cbf_detail_rows = [dict(zip(r_cbf_detail.keys(), r)) for r in r_cbf_detail.fetchall()]
        url = await asyncio.to_thread(export_sample_detail_excel, req.township_name, cbf_detail_rows)
        return {"code": 200, "url": url}

@app.get("/api/export_village_sample_stats")
@app.post("/api/export_village_sample_stats")
async def api_export_village_sample_stats():
    """实时重新统计并导出全县各行政村抽样比例统计表 (.xlsx)"""
    from generate_village_sample_stats import query_village_sample_stats, build_excel
    village_data = await query_village_sample_stats()
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_path = os.path.abspath(os.path.join(base_dir, "..", "全椒县各行政村抽样比例统计表.xlsx"))
    download_path = os.path.abspath(os.path.join(base_dir, "downloads", "全椒县各行政村抽样比例统计表.xlsx"))
    await asyncio.to_thread(build_excel, village_data, [root_path, download_path])
    return {
        "code": 200, 
        "message": "各行政村抽样比例统计表生成成功",
        "url": "/api/download?file=downloads/全椒县各行政村抽样比例统计表.xlsx"
    }

@app.get("/api/export_rectify_att12")
async def api_export_rectify_att12(township_name: str = ""):
    url = await asyncio.to_thread(export_rectify_att12, township_name)
    return {"code": 200, "url": url}

@app.get("/api/export_rectify_att13")
async def api_export_rectify_att13(township_code: str = "", township_name: str = ""):
    neiye_form = {}
    waiye_rows = []
    async with SessionLocal() as session:
        r1 = await session.execute(
            text("SELECT form_data FROM neiye_records WHERE qsdwdm = :code"),
            {"code": township_code}
        )
        row = r1.fetchone()
        if row and row[0]:
            neiye_form = row[0]
        r2 = await session.execute(text("""
            SELECT village_name, group_name, cbfmc,
                   area_acknowledged, rights_correct, bound_correct,
                   member_qualified, self_verified, self_signed, phone_correct,
                   cbfbm_short, dkbm_short, dkmc
            FROM waiye_samples WHERE township_name = :name
        """), {"name": township_name})
        for r in r2.fetchall():
            waiye_rows.append({
                "village_name": r[0],
                "group_name": r[1],
                "cbfmc": r[2],
                "area_acknowledged": r[3],
                "rights_correct": r[4],
                "bound_correct": r[5],
                "member_qualified": r[6],
                "self_verified": r[7],
                "self_signed": r[8],
                "phone_correct": r[9],
                "cbfbm_short": r[10] or "",
                "dkbm_short": r[11] or "",
                "dkmc": r[12] or ""
            })
    url = await asyncio.to_thread(export_rectify_att13, township_name, neiye_form, waiye_rows)
    return {"code": 200, "url": url}



class SpecialDeductionsRequest(BaseModel):
    special1: bool
    special2: bool
    special3: float

@app.get("/api/special_deductions")
async def get_special_deductions():
    async with SessionLocal() as session:
        # 动态解析县级信息
        r_h = await session.execute(text("SELECT qsdwdm, qsdwmc FROM qsdwdmb ORDER BY qsdwdm"))
        county_info, _ = parse_qsdwdmb_hierarchy(r_h.fetchall())
        c_code = county_info.get("code", "341124")

        r = await session.execute(text("SELECT form_data FROM neiye_records WHERE qsdwdm = :code OR level = 'county'"), {"code": c_code})
        row = r.fetchone()
        if row and row[0]:
            fd = row[0]
            return {"code": 200, "data": {
                "special1": fd.get("special1", False),
                "special2": fd.get("special2", False),
                "special3": fd.get("special3", 0.0)
            }}
        return {"code": 200, "data": {"special1": False, "special2": False, "special3": 0.0}}

@app.post("/api/special_deductions")
async def save_special_deductions(req: SpecialDeductionsRequest):
    async with SessionLocal() as session:
        # 动态解析县级信息
        r_h = await session.execute(text("SELECT qsdwdm, qsdwmc FROM qsdwdmb ORDER BY qsdwdm"))
        county_info, _ = parse_qsdwdmb_hierarchy(r_h.fetchall())
        c_code = county_info.get("code", "341124")
        c_name = county_info.get("name", "全椒县")

        r = await session.execute(text("SELECT form_data FROM neiye_records WHERE qsdwdm = :code OR level = 'county'"), {"code": c_code})
        row = r.fetchone()
        fd = row[0] if (row and row[0]) else {}
        fd["special1"] = req.special1
        fd["special2"] = req.special2
        fd["special3"] = req.special3
        
        sql = text('''
            INSERT INTO neiye_records (qsdwdm, qsdwmc, level, form_data, score, updated_at)
            VALUES (:c_code, :c_name, 'county', :fd, 0, CURRENT_TIMESTAMP)
            ON CONFLICT (qsdwdm) DO UPDATE SET
                qsdwmc = EXCLUDED.qsdwmc,
                form_data = EXCLUDED.form_data,
                updated_at = CURRENT_TIMESTAMP
        ''')
        await session.execute(sql, {"c_code": c_code, "c_name": c_name, "fd": json.dumps(fd)})
        await session.commit()
    return {"code": 200, "message": "保存成功"}

# ================= 认证 & 用户管理 API =================

import io
import base64
import random
from PIL import Image, ImageDraw, ImageFont

# 本地验证码临时存储字典: captcha_id -> (code_lower, expire_timestamp)
captcha_store = {}

def create_local_captcha():
    """纯本地生成高清晰防刷图形验证码，0 外部网络依赖"""
    # 排除易混淆字符 0, O, o, 1, I, l
    chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
    code = ''.join(random.choices(chars, k=4))
    width, height = 124, 40
    img = Image.new('RGB', (width, height), color=(244, 246, 249))
    draw = ImageDraw.Draw(img)

    # 尝试加载清晰粗体英文字体，自适应降级
    try:
        font_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arialbd.ttf")
        if not os.path.exists(font_path):
            font_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", "arial.ttf")
        font = ImageFont.truetype(font_path, 26)
    except Exception:
        font = ImageFont.load_default()

    # 绘制轻度平滑干扰线条
    for _ in range(4):
        x1, y1 = random.randint(0, width), random.randint(0, height)
        x2, y2 = random.randint(0, width), random.randint(0, height)
        draw.line((x1, y1, x2, y2), fill=(random.randint(180, 220), random.randint(180, 220), random.randint(190, 230)), width=1)

    # 绘制轻量噪点
    for _ in range(35):
        xy = (random.randint(0, width), random.randint(0, height))
        draw.point(xy, fill=(random.randint(130, 190), random.randint(130, 190), random.randint(150, 210)))

    # 逐字绘制，轻度位置扰动
    for i, char in enumerate(code):
        x = 12 + i * 26 + random.randint(-2, 2)
        y = random.randint(4, 9)
        char_color = (random.randint(25, 90), random.randint(40, 110), random.randint(120, 200))
        draw.text((x, y), char, font=font, fill=char_color)

    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64_image = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode('utf-8')
    return code, b64_image

@app.get("/api/auth/captcha")
async def api_get_captcha():
    """获取纯本地生成的图形验证码"""
    now = time.time()
    # 定期清理过期的验证码缓存（超过 5 分钟）
    expired_keys = [k for k, v in captcha_store.items() if v[1] < now]
    for k in expired_keys:
        captcha_store.pop(k, None)

    code, b64_img = create_local_captcha()
    captcha_id = uuid.uuid4().hex
    # 验证码有效期 5 分钟
    captcha_store[captcha_id] = (code.lower(), now + 300)
    return {
        "code": 200,
        "captcha_id": captcha_id,
        "image": b64_img
    }

class LoginRequest(BaseModel):
    username: str
    password: str
    captcha_id: Optional[str] = ""
    captcha_code: Optional[str] = ""

@app.post("/api/auth/login")
async def api_login(req: LoginRequest, request: Request = None):
    # 1. 纯本地校验图形验证码
    clean_id = (req.captcha_id or "").strip()
    clean_code = (req.captcha_code or "").strip().lower()

    if not clean_id or clean_id not in captcha_store:
        return {"code": 400, "message": "验证码已过期，请点击图片刷新重试"}
    
    correct_code, expire_at = captcha_store.pop(clean_id, (None, 0))
    if time.time() > expire_at:
        return {"code": 400, "message": "验证码已过期，请重新输入"}
    
    if clean_code != correct_code:
        return {"code": 400, "message": "验证码错误，请重新输入"}

    # 2. 账号密码登录
    token, err, user_db = await auth_module.login(req.username, req.password)
    if err:
        return {"code": 401, "message": err}
    perms = await auth_module.get_perms(req.username)
    payload = auth_module._verify_token(token)
    
    # 动态获取用户绑定数据库的县域名称
    county_info, _ = get_county_and_townships_sync(db_name=user_db)
    county_name = county_info.get("name", user_db)
    
    # 记录登录审计
    record_check_audit(
        module_type="用户认证",
        action_type="账号登录成功",
        target_desc=f"登录系统工作台 (数据库: {user_db} - {county_name})",
        details=f"角色: {payload.get('role', 'user')}, 分配数据库: {user_db}",
        request=request,
        username=req.username
    )
    
    return {"code": 200, "token": token, "username": req.username,
            "role": payload.get("role","user"), 
            "target_db": user_db,
            "county_name": county_name,
            "perms": perms}

@app.get("/api/auth/check")
async def api_check_auth(request: Request):
    """
    检查当前 Token 的有效性（包括签名、未过期、以及密码未被修改）。
    若密码已被修改，Token 中的 pwd_ver 与数据库不一致，直接返回 401。
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录或缺少身份凭证")
    token = auth_header.split(" ", 1)[1].strip()
    payload = await auth_module.verify_token_active(token)
    if not payload:
        raise HTTPException(status_code=401, detail="登录凭证已失效或密码已被修改，请重新登录")
    perms = await auth_module.get_perms(payload.get("sub", ""))
    user_db = payload.get("target_db") or current_db_ctx.get()
    county_info, _ = get_county_and_townships_sync(db_name=user_db)
    county_name = county_info.get("name", user_db)
    return {
        "code": 200,
        "valid": True,
        "username": payload.get("sub"),
        "role": payload.get("role", "user"),
        "target_db": user_db,
        "county_name": county_name,
        "perms": perms
    }

class ChangePasswordRequest(BaseModel):
    username: str
    old_password: str
    new_password: str

class ResetPasswordRequest(BaseModel):
    username: str
    new_password: str

class CreateUserRequest(BaseModel):
    username: str
    role: str = "user"
    password: str = "123456"
    target_db: Optional[str] = ""

class BatchCreateRequest(BaseModel):
    usernames: List[str]
    target_db: Optional[str] = ""

class SetUserDbRequest(BaseModel):
    username: str
    target_db: str

class SetPermsRequest(BaseModel):
    username: str
    perms: dict

@app.get("/api/auth/perms")
async def api_get_perms(username: str = ""):
    if not username:
        return {"code": 400, "message": "missing username"}
    perms = await auth_module.get_perms(username)
    return {"code": 200, "perms": perms}

@app.post("/api/auth/set_perms")
async def api_set_perms(req: SetPermsRequest):
    await auth_module.set_perms(req.username, req.perms)
    return {"code": 200}

@app.post("/api/auth/set_user_db")
async def api_set_user_db(req: SetUserDbRequest):
    await auth_module.set_user_target_db(req.username, req.target_db)
    return {"code": 200, "message": "工作数据库分配成功"}

@app.get("/api/auth/users")
async def api_list_users():
    users = await auth_module.list_users()
    return {"code": 200, "users": users}

@app.post("/api/auth/create_user")
async def api_create_user(req: CreateUserRequest):
    try:
        cur_db = current_db_ctx.get() or load_config().get("db_name", "quanjiao")
        target_db = (req.target_db or cur_db).strip()
        ok, err = await auth_module.create_user(req.username, req.role, req.password, target_db)
        if not ok:
            return {"code": 400, "message": err}
        return {"code": 200, "target_db": target_db}
    except Exception as e:
        print(f"api_create_user error: {e}")
        return {"code": 400, "message": f"创建账号失败: {str(e)}"}

@app.post("/api/auth/batch_create")
async def api_batch_create(req: BatchCreateRequest):
    try:
        cur_db = current_db_ctx.get() or load_config().get("db_name", "quanjiao")
        target_db = (req.target_db or cur_db).strip()
        results = []
        for uname in req.usernames:
            uname = uname.strip()
            if not uname:
                continue
            ok, err = await auth_module.create_user(uname, target_db=target_db)
            results.append({"username": uname, "ok": ok, "err": err or ""})
        return {"code": 200, "results": results, "target_db": target_db}
    except Exception as e:
        print(f"api_batch_create error: {e}")
        return {"code": 400, "message": f"批量创建失败: {str(e)}"}

@app.post("/api/auth/delete_user")
async def api_delete_user(req: CreateUserRequest, request: Request = None):
    clean_u = (req.username or "").strip()
    ok, err = await auth_module.delete_user(clean_u)
    if not ok:
        return {"code": 400, "message": err}
    
    # 记录删除账号审计
    record_check_audit(
        module_type="用户认证",
        action_type="删除系统账号",
        target_desc=f"账号: {clean_u}",
        details=f"成功从 sys_users 及 sys_permissions 中永久级联删除账号 [{clean_u}]",
        request=request
    )
    return {"code": 200, "message": f"账号 {clean_u} 已成功删除"}

@app.post("/api/auth/reset_password")
async def api_reset_password(req: ResetPasswordRequest):
    await auth_module.reset_password(req.username, req.new_password)
    return {"code": 200}

@app.post("/api/auth/change_password")
async def api_change_password(req: ChangePasswordRequest):
    ok, err = await auth_module.change_password(req.username, req.old_password, req.new_password)
    if not ok:
        return {"code": 400, "message": err}
    return {"code": 200}

@app.get("/api/auth/user_perms_all")
async def api_user_perms_all():
    """Return all users with their permissions for admin view."""
    users = await auth_module.list_users()
    result = []
    for u in users:
        perms = await auth_module.get_perms(u["username"])
        result.append({**u, "perms": perms})
    return {"code": 200, "users": result}

# ================= 凭证图片上传 API =================
os.makedirs(os.path.join(os.path.dirname(__file__), "uploads"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "uploads")), name="uploads")

def _process_and_save_image(content: bytes, target_path: str):
    """在后台独立线程中处理图像，避免阻塞主事件循环"""
    try:
        img = Image.open(io.BytesIO(content))
        img = ImageOps.exif_transpose(img) # 纠正手机拍照旋转角度
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        
        # 长边超过 1920 时按比例等比缩放
        max_size = 1920
        if max(img.size) > max_size:
            img.thumbnail((max_size, max_size), Image.Resampling.BILINEAR)
        
        # 保存 JPEG，去掉极耗 CPU 的 optimize=True，兼顾质量与极致保存速度
        img.save(target_path, "JPEG", quality=82)
    except Exception:
        # 如非标准图像格式直接保存原二进制
        with open(target_path, "wb") as f:
            f.write(content)

@app.post("/api/upload_evidence")
async def api_upload_evidence(file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = f"{uuid.uuid4().hex}.jpg"
        target_path = os.path.join(os.path.dirname(__file__), "uploads", filename)
        
        # 移入异步工作线程池执行图像解码、旋转与写入，消除主线程卡顿
        await asyncio.to_thread(_process_and_save_image, content, target_path)
                
        return {"code": 200, "url": f"/uploads/{filename}", "filename": filename}
    except Exception as e:
        return {"code": 500, "message": f"上传处理失败: {str(e)}"}
class DeleteEvidenceRequest(BaseModel):
    url: str

@app.post("/api/delete_evidence")
async def api_delete_evidence(req: DeleteEvidenceRequest):
    url = req.url
    if not url:
        return {"code": 400, "message": "缺少URL参数"}
    try:
        if url.startswith("/uploads/"):
            filename = os.path.basename(url)
            if ".." not in filename and "/" not in filename and "\\" not in filename:
                filepath = os.path.join(os.path.dirname(__file__), "uploads", filename)
                if os.path.exists(filepath) and os.path.isfile(filepath):
                    os.remove(filepath)
        return {"code": 200, "message": "凭证已成功删除"}
    except Exception as e:
        return {"code": 500, "message": f"删除凭证异常: {str(e)}"}

# ================= 询问笔录 (现场问询) =================

class VillagePhotosSaveRequest(BaseModel):
    village_code: str
    township_name: Optional[str] = ""
    village_name: Optional[str] = ""
    photos: List[str] = []

@app.get("/api/waiye/village_photos")
async def get_village_photos(village_code: str):
    """获取指定行政村上传的现场会照片列表"""
    clean_vcode = str(village_code or "").strip()
    if not clean_vcode:
        return {"code": 400, "message": "村级代码不能为空"}
    v_target = f"VILLAGE_{clean_vcode}"

    async with SessionLocal() as session:
        res = await session.execute(
            text("SELECT form_data, township_name, village_name FROM waiye_inquiries WHERE cbfbm = :t LIMIT 1"),
            {"t": v_target}
        )
        row = res.fetchone()
        if row and row[0]:
            fd = row[0]
            photos = fd.get("photos") or []
            return {
                "code": 200, 
                "photos": photos,
                "township_name": row[1] or "",
                "village_name": row[2] or ""
            }
        return {"code": 200, "photos": [], "township_name": "", "village_name": ""}

@app.post("/api/waiye/village_photos")
async def save_village_photos(req: VillagePhotosSaveRequest):
    """保存或更新指定行政村的现场会核查照片列表"""
    clean_vcode = str(req.village_code or "").strip()
    if not clean_vcode:
        return {"code": 400, "message": "村级代码不能为空"}
    v_target = f"VILLAGE_{clean_vcode}"
    
    # 严格过滤有效服务器存储路径，杜绝临时 blob: 或 data: 等死链入库
    clean_photos = []
    for p in req.photos:
        if not p or not isinstance(p, str):
            continue
        p_clean = p.strip()
        if (p_clean.startswith("/uploads/") or "uploads/" in p_clean) and not p_clean.startswith("blob:") and not p_clean.startswith("data:"):
            if p_clean not in clean_photos:
                clean_photos.append(p_clean)

    async with SessionLocal() as session:
        res = await session.execute(
            text("SELECT id, form_data FROM waiye_inquiries WHERE cbfbm = :t LIMIT 1"),
            {"t": v_target}
        )
        row = res.fetchone()
        if row:
            fd = row[1] or {}
            fd["photos"] = clean_photos
            await session.execute(
                text("UPDATE waiye_inquiries SET form_data = :fd, township_name = :tn, village_name = :vn, updated_at = CURRENT_TIMESTAMP WHERE id = :id"),
                {"fd": json.dumps(fd), "tn": req.township_name or "", "vn": req.village_name or "", "id": row[0]}
            )
        else:
            fd = {"photos": clean_photos}
            await session.execute(
                text("""
                    INSERT INTO waiye_inquiries (cbfbm, township_name, village_name, group_name, cbfmc, form_data)
                    VALUES (:t, :tn, :vn, '行政村现场会', '行政村现场会', :fd)
                """),
                {"t": v_target, "tn": req.township_name or "", "vn": req.village_name or "", "fd": json.dumps(fd)}
            )
        await session.commit()
    return {"code": 200, "message": "村级现场照片保存成功", "photos": clean_photos}

class ExportVillagePhotosRequest(BaseModel):
    village_code: Optional[str] = ""
    township_name: Optional[str] = ""
    village_name: Optional[str] = ""
    photos: Optional[List[str]] = None

@app.post("/api/export_village_meeting_photos")
async def api_export_village_meeting_photos(req: ExportVillagePhotosRequest):
    """导出指定行政村现场会照片文档 (.docx)"""
    clean_vcode = str(req.village_code or "").strip()
    t_name = (req.township_name or "").strip()
    v_name = (req.village_name or "").strip()
    photos = req.photos or []

    async with SessionLocal() as session:
        if clean_vcode and not photos:
            v_target = f"VILLAGE_{clean_vcode}"
            res = await session.execute(
                text("SELECT form_data, township_name, village_name FROM waiye_inquiries WHERE cbfbm = :t LIMIT 1"),
                {"t": v_target}
            )
            row = res.fetchone()
            if row:
                fd = row[0] or {}
                photos = fd.get("photos") or []
                if not t_name: t_name = row[1] or ""
                if not v_name: v_name = row[2] or ""

        # 如果没有传乡镇名和村名，尝试通过代码反查
        if (not t_name or not v_name) and clean_vcode:
            r_q = await session.execute(
                text("SELECT qsdwdm, qsdwmc FROM qsdwdmb WHERE qsdwdm::text LIKE :code LIMIT 1"),
                {"code": f"{clean_vcode[:12]}%"}
            )
            q_row = r_q.fetchone()
            if q_row:
                v_name = v_name or q_row[1]

    url = await asyncio.to_thread(export_village_meeting_photos, t_name, v_name, photos)
    return {"code": 200, "url": url}

class InquirySaveRequest(BaseModel):
    cbfbm: str
    township_name: Optional[str] = ""
    village_name: Optional[str] = ""
    group_name: Optional[str] = ""
    cbfmc: Optional[str] = ""
    form_data: dict

@app.get("/api/waiye/inquiry")
async def get_inquiry(cbfbm: str):
    from database import SessionLocal
    from sqlalchemy import text
    async with SessionLocal() as session:
        res = await session.execute(text("SELECT form_data, signature_url, scan_file_url FROM waiye_inquiries WHERE cbfbm = :cbfbm LIMIT 1"), {"cbfbm": cbfbm})
        row = res.fetchone()
        if row:
            return {"code": 200, "data": {"form_data": row[0] or {}, "signature_url": row[1] or "", "scan_file_url": row[2] or ""}}
        return {"code": 200, "data": {"form_data": {}, "signature_url": "", "scan_file_url": ""}}

@app.post("/api/waiye/inquiry")
async def save_inquiry(req: InquirySaveRequest):
    import json
    import base64
    from database import SessionLocal
    from sqlalchemy import text
    
    # 仅保留被询问人签名与询问人签名（已取消村民代表签名）
    for sign_key in ['bxwrqm', 'xwrqm']:
        sig_data = req.form_data.get(sign_key, '')
        if sig_data and sig_data.startswith('data:image'):
            try:
                os.makedirs("uploads/signatures", exist_ok=True)
                head, base64_str = sig_data.split(',', 1)
                img_data = base64.b64decode(base64_str)
                with open(os.path.join("uploads", "signatures", f"{req.cbfbm}_{sign_key}.png"), "wb") as f:
                    f.write(img_data)
                req.form_data[sign_key] = f"/api/download?file=uploads/signatures/{req.cbfbm}_{sign_key}.png"
            except Exception as e:
                print(f"Failed to save {sign_key}:", e)

    # 严格清理 form_data 中的 photos 数组，防范 blob: 临时链接落库
    if "photos" in req.form_data and isinstance(req.form_data["photos"], list):
        clean_inq_photos = []
        for p in req.form_data["photos"]:
            if not p or not isinstance(p, str):
                continue
            p_clean = p.strip()
            if (p_clean.startswith("/uploads/") or "uploads/" in p_clean) and not p_clean.startswith("blob:") and not p_clean.startswith("data:"):
                if p_clean not in clean_inq_photos:
                    clean_inq_photos.append(p_clean)
        req.form_data["photos"] = clean_inq_photos

    # 若前端未传区划信息，从已有记录或承包方表反查补全
    t_name = (req.township_name or "").strip()
    v_name = (req.village_name or "").strip()
    g_name = (req.group_name or "").strip()
    cbfmc  = (req.cbfmc or "").strip()

    async with SessionLocal() as session:
        res = await session.execute(text("SELECT id, township_name, village_name, group_name, cbfmc FROM waiye_inquiries WHERE cbfbm = :cbfbm LIMIT 1"), {"cbfbm": req.cbfbm})
        row = res.fetchone()

        # 若区划信息缺失，先从已有记录补，再从承包方表补
        if not t_name and row and row[1]:
            t_name = row[1]
        if not v_name and row and row[2]:
            v_name = row[2]
        if not g_name and row and row[3]:
            g_name = row[3]
        if not cbfmc and row and row[4]:
            cbfmc = row[4]
        if not (t_name and v_name and g_name and cbfmc):
            try:
                # 1. 优先从 waiye_samples 补全
                sample_res = await session.execute(
                    text("SELECT township_name, village_name, group_name, cbfmc FROM waiye_samples WHERE cbfbm = :cbfbm LIMIT 1"),
                    {"cbfbm": req.cbfbm}
                )
                sample_row = sample_res.fetchone()
                if sample_row:
                    if not t_name: t_name = sample_row[0] or ""
                    if not v_name: v_name = sample_row[1] or ""
                    if not g_name: g_name = sample_row[2] or ""
                    if not cbfmc:  cbfmc  = sample_row[3] or ""
                # 2. 若承包方名称仍为空，从 cbf 表补全
                if not cbfmc:
                    cbf_res = await session.execute(
                        text("SELECT cbfmc FROM cbf WHERE cbfbm = :cbfbm LIMIT 1"),
                        {"cbfbm": req.cbfbm}
                    )
                    cbf_row = cbf_res.fetchone()
                    if cbf_row and cbf_row[0]:
                        cbfmc = cbf_row[0]
            except Exception as ex:
                print("Fallback info lookup error:", ex)

        if row:
            await session.execute(text("""
                UPDATE waiye_inquiries 
                SET form_data = :form_data, updated_at = CURRENT_TIMESTAMP
                WHERE cbfbm = :cbfbm
            """), {"form_data": json.dumps(req.form_data), "cbfbm": req.cbfbm})
        else:
            await session.execute(text("""
                INSERT INTO waiye_inquiries (cbfbm, township_name, village_name, group_name, cbfmc, form_data)
                VALUES (:cbfbm, :t, :v, :g, :m, :form_data)
            """), {"cbfbm": req.cbfbm, "t": t_name, "v": v_name, "g": g_name, "m": cbfmc, "form_data": json.dumps(req.form_data)})
        await session.commit()
    return {"code": 200, "message": "保存成功"}

@app.post("/api/waiye/inquiry_scan")
async def upload_inquiry_scan(cbfbm: str = Form(...), cbfmc: str = Form(""), file: UploadFile = File(...)):
    from database import SessionLocal
    from sqlalchemy import text
    os.makedirs("uploads/inquiries", exist_ok=True)
    ext = file.filename.split('.')[-1]
    filename = f"{cbfbm}_{cbfmc}.{ext}" if cbfmc else f"{cbfbm}_scan.{ext}"
    file_path = os.path.join("uploads/inquiries", filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    url = f"/api/download?file=uploads/inquiries/{filename}"
    
    async with SessionLocal() as session:
        res = await session.execute(text("SELECT id FROM waiye_inquiries WHERE cbfbm = :cbfbm LIMIT 1"), {"cbfbm": cbfbm})
        if res.fetchone():
            await session.execute(text("UPDATE waiye_inquiries SET scan_file_url = :url WHERE cbfbm = :cbfbm"), {"url": url, "cbfbm": cbfbm})
        else:
            await session.execute(text("INSERT INTO waiye_inquiries (cbfbm, scan_file_url) VALUES (:cbfbm, :url)"), {"cbfbm": cbfbm, "url": url})
        await session.commit()
    return {"code": 200, "message": "上传成功", "url": url}

class ExportInquiryRequest(BaseModel):
    cbfbm: str
    form_data: Optional[dict] = None
    photos: Optional[List[str]] = None

@app.post("/api/export_waiye_inquiry")
async def api_export_waiye_inquiry(req: ExportInquiryRequest):
    from database import SessionLocal
    from sqlalchemy import text
    async with SessionLocal() as session:
        res = await session.execute(text("SELECT * FROM waiye_inquiries WHERE cbfbm = :cbfbm"), {"cbfbm": req.cbfbm})
        row = res.fetchone()
        if not row and not req.form_data:
            return {"code": 404, "message": "没有找到该农户的问询记录"}
            
        r_cbf = await session.execute(text("SELECT cbfzjhm, lxdh FROM cbf WHERE cbfbm = :cbfbm"), {"cbfbm": req.cbfbm})
        cbf_row = r_cbf.fetchone()
        lxdh = str(cbf_row[1]) if cbf_row and cbf_row[1] else ""
        gender = "男"
        
        # Count parcels
        r_dk = await session.execute(text("SELECT COUNT(*), SUM(scmj) FROM waiye_samples WHERE cbfbm = :cbfbm"), {"cbfbm": req.cbfbm})
        dk_row = r_dk.fetchone()
        dk_cnt = dk_row[0] if dk_row else 0
        
        # Get HTZMJ (from cbdkxx)
        r_ht = await session.execute(text("SELECT SUM(htmjm) FROM cbdkxx WHERE cbfbm::text = :cbfbm"), {"cbfbm": req.cbfbm})
        ht_row = r_ht.fetchone()
        ht_mj = ht_row[0] if ht_row and ht_row[0] else 0.0
        
        # 获取实际承包方名称
        r_samp = await session.execute(text("SELECT cbfmc FROM waiye_samples WHERE cbfbm = :cbfbm LIMIT 1"), {"cbfbm": req.cbfbm})
        samp_row = r_samp.fetchone()
        real_cbfmc = samp_row[0] if (samp_row and samp_row[0]) else ((row[5] if row else "") or "")
        
        fd = req.form_data or (row[6] if row else {}) or {}
        bxwr_name = fd.get("bxwr") or fd.get("cbfmc") or real_cbfmc
        
        # 提取照片（优先使用传入的现场照片列表，双重兜底）
        photos = req.photos or fd.get("photos") or []
        
        data = {
            "cbfbm": req.cbfbm,
            "cbfmc": real_cbfmc,
            "bxwr": bxwr_name,
            "township_name": (row[2] if row else "") or fd.get("township_name", ""),
            "village_name": (row[3] if row else "") or fd.get("village_name", ""),
            "group_name": (row[4] if row else "") or fd.get("group_name", ""),
            "lxdh": fd.get("lxdh", lxdh),
            "gender": fd.get("gender", gender),
            "dk_cnt": dk_cnt,
            "scmj": ht_mj,
            "form_data": fd,
            "photos": photos
        }
    from doc_exporter import export_waiye_inquiry
    url = await asyncio.to_thread(export_waiye_inquiry, data)
    return {"code": 200, "url": url}
from voucher_exporter import export_voucher

class ExportNeiyeVoucherRequest(BaseModel):
    qsdwdm: str
    qsdwmc: str
    level: str
    form_data: dict

@app.post("/api/export_neiye_voucher")
async def api_export_neiye_voucher(req: ExportNeiyeVoucherRequest):
    url = await asyncio.to_thread(export_voucher, req.qsdwdm, req.qsdwmc, req.form_data)
    if url:
        return {"code": 200, "url": url}
    else:
        return {"code": 500, "message": "Failed to generate voucher record"}

# ── 帮助文件 ────────────────────────────────────────────────────────────
HELP_DIR = os.path.join(os.path.dirname(__file__), "help")

@app.get("/api/help/files")
async def list_help_files():
    files = []
    for f in os.listdir(HELP_DIR):
        fp = os.path.join(HELP_DIR, f)
        if os.path.isfile(fp):
            stat = os.stat(fp)
            files.append({"name": f, "size": stat.st_size, "mtime": stat.st_mtime})
    return {"code": 200, "files": files}

@app.get("/api/help/download")
async def download_help_file(file: str):
    import urllib.parse
    file = urllib.parse.unquote(file)
    # 仅允许文件名，防止路径穿越
    if not file or "/" in file or "\\" in file or ".." in file:
        return {"code": 400, "message": "非法文件名"}
    fp = os.path.join(HELP_DIR, file)
    if os.path.exists(fp) and os.path.isfile(fp):
        from fastapi.responses import FileResponse
        return FileResponse(fp, filename=os.path.basename(fp), content_disposition_type="attachment")
    return {"code": 404, "message": "文件不存在"}

@app.get("/api/help/preview")
async def preview_help_file(file: str):
    import urllib.parse
    file = urllib.parse.unquote(file)
    if not file or "/" in file or "\\" in file or ".." in file:
        return {"code": 400, "message": "非法文件名"}
    fp = os.path.join(HELP_DIR, file)
    if os.path.exists(fp) and os.path.isfile(fp):
        from fastapi.responses import FileResponse
        return FileResponse(fp, content_disposition_type="inline")
    return {"code": 404, "message": "文件不存在"}
