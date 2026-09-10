import base64
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
import uuid
import shutil, io
from PIL import Image, ImageOps
from doc_exporter import (
    export_docs, export_att4, export_att5, export_waiye_att8, export_waiye_att9,
    export_neiye_att6_township, export_neiye_att6_county, export_neiye_att7,
    export_rectify_att12, export_rectify_att13, sanitize_filename
)
# -*- coding: utf-8 -*-
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import os
import random
import math
import json
import pandas as pd
from sqlalchemy import text, create_engine
from database import SessionLocal, load_config, switch_database, list_available_databases, build_sync_url, parse_qsdwdmb_hierarchy, get_base_dir
from data_importer import import_data_from_path, get_import_progress, query_import_summary, ensure_database_and_tables, validate_source_package
import auth as auth_module

from batch_exporter import run_batch_export

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
    try:
        url = await run_batch_export(
            req.level, req.township_code, req.township_name, req.attachments
        )
        if url:
            return {"code": 200, "url": url}
        else:
            return {"code": 500, "message": "批量打包失败"}
    except Exception as e:
        print("Batch export error:", e)
        return {"code": 500, "message": f"服务器异常: {str(e)}"}

@app.on_event("startup")
async def startup_event():
    await auth_module.init_auth_db()
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

@app.get("/")
async def root():
    return {"message": "Welcome to 全椒县二轮延包验收系统 API"}

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
    county_name = cfg.get("county_name", "全椒县")
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
    target_county = req.county_name.strip() if (req.county_name and req.county_name.strip()) else target_db
    
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
    async with SessionLocal() as session:
        sql = text("SELECT cbfbm, cbfmc, lxdh FROM cbf WHERE cbfbm::text LIKE :code ORDER BY cbfbm")
        result = await session.execute(sql, {"code": f"{qsdwdm}%"})
        rows = result.fetchall()
        data = [{"cbfbm": str(r[0]), "cbfmc": r[1], "lxdh": r[2]} for r in rows]
        return {"code": 200, "data": data}

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

        res_sampled = await session.execute(text("SELECT DISTINCT township_name FROM waiye_samples"))
        sampled_names = set(r[0] for r in res_sampled.fetchall() if r[0])

        sampled_townships = [t for t in townships if t["name"] in sampled_names]

        return {"code": 200, "county": county, "townships": sampled_townships}

@app.get("/api/contractor_count")
async def get_contractor_count(group_code: str):
    async with SessionLocal() as session:
        sql = text("SELECT COUNT(*) FROM cbf WHERE cbfbm::text LIKE :code")
        res = await session.execute(sql, {"code": f"{group_code}%"})
        count = res.scalar()
        return {"code": 200, "count": count}

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
        
        for g in sampled_groups:
            g_code = str(g["code"])
            tz_name = g.get("tz_name", req.township_name)
            sql = text("SELECT cbfbm, cbfmc, lxdh FROM cbf WHERE cbfbm::text LIKE :code")
            res = await session.execute(sql, {"code": f"{g_code}%"})
            cbfs = res.fetchall()
            total_cbf = len(cbfs)
            
            # 使用统一抽样数量算法
            sample_size = calc_sample_size(total_cbf, req.manual_sample_count if req.mode == 1 else None)
            
            if sample_size > 0:
                sampled = random.sample(cbfs, sample_size)
                stats.append({
                    "序号": len(stats) + 1,
                    "乡镇名称": tz_name,
                    "村名称": g["v_name"], 
                    "组名称": g["name"],
                    "发包方总户数": total_cbf,
                    "抽样农户数5%": sample_size
                })
                
                # Delete existing samples for this group
                await session.execute(text("DELETE FROM waiye_samples WHERE group_code = :g_code"), {"g_code": g_code})
                
                for idx, c in enumerate(sampled):
                    sql_dk = text('''
                        SELECT b.dkbm, a.dkmc, b.htmjm 
                        FROM cbdkxx b
                        LEFT JOIN dkxx_shp_attrs a ON a.dkbm = b.dkbm
                        WHERE b.cbfbm::text = :cbfbm
                    ''')
                    res_dk = await session.execute(sql_dk, {"cbfbm": c[0]})
                    dks = res_dk.fetchall()
                    if not dks:
                        await session.execute(text("""
                            INSERT INTO waiye_samples (
                                township_name, village_name, group_name, group_code,
                                cbfmc, cbfbm, cbfbm_short, lxdh,
                                dkmc, dkbm, dkbm_short, scmj
                            ) VALUES (
                                :t_name, :v_name, :g_name, :g_code,
                                :cbfmc, :cbfbm, :cbfbm_short, :lxdh,
                                '', '', '', 0
                            )
                        """), {
                            "t_name": tz_name, "v_name": g["v_name"], "g_name": g["name"], "g_code": g_code,
                            "cbfmc": c[1], "cbfbm": str(c[0]), "cbfbm_short": str(c[0])[-4:] if c[0] else "",
                            "lxdh": str(c[2]) if c[2] else ""
                        })
                    for dk in dks:
                        await session.execute(text("""
                            INSERT INTO waiye_samples (
                                township_name, village_name, group_name, group_code,
                                cbfmc, cbfbm, cbfbm_short, lxdh,
                                dkmc, dkbm, dkbm_short, scmj
                            ) VALUES (
                                :t_name, :v_name, :g_name, :g_code,
                                :cbfmc, :cbfbm, :cbfbm_short, :lxdh,
                                :dkmc, :dkbm, :dkbm_short, :scmj
                            )
                        """), {
                            "t_name": tz_name, "v_name": g["v_name"], "g_name": g["name"], "g_code": g_code,
                            "cbfmc": c[1], "cbfbm": str(c[0]), "cbfbm_short": str(c[0])[-4:] if c[0] else "",
                            "lxdh": str(c[2]) if c[2] else "",
                            "dkmc": dk[1] or "",
                            "dkbm": str(dk[0]) if dk[0] else "",
                            "dkbm_short": str(dk[0])[-5:] if dk[0] else "",
                            "scmj": float(dk[2]) if dk[2] is not None else 0.0
                        })
                        
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
    file = urllib.parse.unquote(file)
    if not os.path.isabs(file):
        backend_file = os.path.join(os.path.dirname(__file__), file)
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
    """预检上传的 Excel 抽样表格中各发包方的指定抽样户数是否符合验收规范要求"""
    os.makedirs("uploads/抽样表", exist_ok=True)
    temp_path = os.path.join("uploads/抽样表", f"check_{uuid.uuid4().hex}_{file.filename}")
    with open(temp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    try:
        df = pd.read_excel(temp_path)
    except Exception as e:
        if os.path.exists(temp_path): os.remove(temp_path)
        return {"code": 400, "message": "无法解析Excel文件，请检查文件格式是否有效"}
    finally:
        if os.path.exists(temp_path):
            try: os.remove(temp_path)
            except: pass
        
    required = ["发包方编码", "乡镇名", "村名", "组名"]
    for r in required:
        if r not in df.columns:
            return {"code": 400, "message": f"表格缺少必要表头列: 【{r}】"}
            
    async with SessionLocal() as session:
        inspected_items = []
        insufficient_list = []
        exceeded_list = []
        
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
            item_data = {
                "row_idx": idx + 1,
                "group_code": g_code,
                "township_name": g_town,
                "village_name": g_vill,
                "group_name": g_name,
                "group_desc": group_desc,
                **check_res
            }
            inspected_items.append(item_data)
            
            if check_res["is_insufficient"]:
                insufficient_list.append(item_data)
            elif check_res["status"] == "exceeded":
                exceeded_list.append(item_data)
                
        return {
            "code": 200,
            "data": {
                "total_groups": len(inspected_items),
                "insufficient_count": len(insufficient_list),
                "exceeded_count": len(exceeded_list),
                "has_insufficient": len(insufficient_list) > 0,
                "insufficient_list": insufficient_list,
                "exceeded_list": exceeded_list,
                "details": inspected_items
            }
        }

@app.post("/api/sample_by_excel")
async def do_sample_by_excel(file: UploadFile = File(...)):
    os.makedirs("uploads/抽样表", exist_ok=True)
    file_path = os.path.join("uploads/抽样表", file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    try:
        df = pd.read_excel(file_path)
    except Exception as e:
        return {"code": 400, "message": "无法解析Excel文件"}
        
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

        # 2. 合规核验通过，开始执行抽样与写库
        stats = []
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
                
                await session.execute(text("DELETE FROM waiye_samples WHERE group_code = :g_code"), {"g_code": g_code})
                
                for c in sampled:
                    sql_dk = text('''
                        SELECT b.dkbm, a.dkmc, b.htmjm 
                        FROM cbdkxx b
                        LEFT JOIN dkxx_shp_attrs a ON a.dkbm = b.dkbm
                        WHERE b.cbfbm::text = :cbfbm
                    ''')
                    res_dk = await session.execute(sql_dk, {"cbfbm": c[0]})
                    dks = res_dk.fetchall()
                    if not dks:
                        await session.execute(text("""
                            INSERT INTO waiye_samples (
                                township_name, village_name, group_name, group_code,
                                cbfmc, cbfbm, cbfbm_short, lxdh,
                                dkmc, dkbm, dkbm_short, scmj
                            ) VALUES (
                                :t_name, :v_name, :g_name, :g_code,
                                :cbfmc, :cbfbm, :cbfbm_short, :lxdh,
                                '', '', '', 0
                            )
                        """), {
                            "t_name": g_town, "v_name": g_vill, "g_name": g_name, "g_code": g_code,
                            "cbfmc": c[1], "cbfbm": str(c[0]), "cbfbm_short": str(c[0])[-4:] if c[0] else "",
                            "lxdh": str(c[2]) if c[2] else ""
                        })
                    for dk in dks:
                        await session.execute(text("""
                            INSERT INTO waiye_samples (
                                township_name, village_name, group_name, group_code,
                                cbfmc, cbfbm, cbfbm_short, lxdh,
                                dkmc, dkbm, dkbm_short, scmj
                            ) VALUES (
                                :t_name, :v_name, :g_name, :g_code,
                                :cbfmc, :cbfbm, :cbfbm_short, :lxdh,
                                :dkmc, :dkbm, :dkbm_short, :scmj
                            )
                        """), {
                            "t_name": g_town, "v_name": g_vill, "g_name": g_name, "g_code": g_code,
                            "cbfmc": c[1], "cbfbm": str(c[0]), "cbfbm_short": str(c[0])[-4:] if c[0] else "",
                            "lxdh": str(c[2]) if c[2] else "",
                            "dkmc": dk[1] or "",
                            "dkbm": str(dk[0]) if dk[0] else "",
                            "dkbm_short": str(dk[0])[-5:] if dk[0] else "",
                            "scmj": float(dk[2]) if dk[2] is not None else 0.0
                        })
        
        await session.commit()
        url_att5 = await asyncio.to_thread(export_att5, stats, township_code, township_name)
        
        return {
            "code": 200, 
            "message": "抽样成功！抽样统计表已生成，抽样数据已保存至外业核查数据库。",
            "stats": stats,
            "urls": [url_att5]
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

# ================= 内业核查 API =================

class NeiyeSaveRequest(BaseModel):
    qsdwdm: str
    qsdwmc: str
    level: str
    form_data: dict
    score: float

@app.post("/api/save_neiye")
async def save_neiye(req: NeiyeSaveRequest):
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
    form_data: Optional[dict] = None

@app.post("/api/export_neiye_att6")
async def api_export_neiye_att6(req: ExportNeiyeAtt6Request):
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
        else:
            url = await asyncio.to_thread(export_neiye_att6_township, req.qsdwmc, form_data)
            
        return {"code": 200, "url": url}
    except Exception as e:
        print(f"api_export_neiye_att6 error: {e}")
        return {"code": 500, "message": f"生成附件6失败: {str(e)}"}

@app.get("/api/export_neiye_att7")
async def api_export_neiye_att7():
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
        
    url = await asyncio.to_thread(export_neiye_att7, records_dict)
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
                g_children = [
                    {
                        "text": f"{g['name']} ({g['cbf_count']}户/{g['dk_count']}地块)",
                        "value": g["code"],
                        "group_name": g["name"],
                        "group_code": g["code"],
                        "village_name": v_name,
                        "township_name": t_name,
                        "cbf_count": g["cbf_count"],
                        "dk_count": g["dk_count"]
                    }
                    for g in g_list
                ]
                v_children.append({
                    "text": v_name,
                    "value": v_name,
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
async def save_waiye_signature(req: SignatureSaveRequest):
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
async def save_waiye_records(req: WaiyeSaveRequest):
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
        return {"code": 200, "message": "保存成功"}

class ExportWaiyeAtt8Request(BaseModel):
    township_name: str
    village_name: Optional[str] = None
    group_name: Optional[str] = None
    group_code: Optional[str] = None

@app.post("/api/export_waiye_att8")
async def api_export_waiye_att8(req: ExportWaiyeAtt8Request):
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
            
        return {
            "code": 200, 
            "url": urls[0] if urls else "",
            "urls": urls,
            "count": len(urls),
            "message": f"已成功生成 {len(urls)} 份附件8文档！"
        }

@app.get("/api/export_waiye_att9")
async def api_export_waiye_att9():
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
    return {"code": 200, "url": url}

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
    from score_service import get_all_township_scores
    async with SessionLocal() as session:
        scores, c_mech, has_c = await get_all_township_scores(session)
        
    county_mech = 15.0
    county_prog_nei = 30.0
    county_policy = 15.0
    county_effect_nei = 10.0
    county_prog_wai = 20.0
    county_effect_wai = 10.0
    
    if len(scores) > 0:
        mech_sum = sum(s["mech"] for s in scores.values())
        if has_c:
            county_mech = (mech_sum + c_mech) / (len(scores) + 1)
        else:
            county_mech = mech_sum / len(scores)
            
        county_prog_nei = sum(s["prog_nei"] for s in scores.values()) / len(scores)
        county_policy = sum(s["policy"] for s in scores.values()) / len(scores)
        county_effect_nei = sum(s["effect_nei"] for s in scores.values()) / len(scores)
        county_prog_wai = sum(s["prog_wai"] for s in scores.values()) / len(scores)
        county_effect_wai = sum(s["effect_wai"] for s in scores.values()) / len(scores)
        
    return {
        "code": 200,
        "data": {
            "mech": round(county_mech, 1),
            "prog_nei": round(county_prog_nei, 1),
            "policy": round(county_policy, 1),
            "effect_nei": round(county_effect_nei, 1),
            "prog_wai": round(county_prog_wai, 1),
            "effect_wai": round(county_effect_wai, 1)
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
    from score_service import get_all_township_scores
    from doc_exporter_score import export_att11
    async with SessionLocal() as session:
        scores, c_mech, has_c = await get_all_township_scores(session)
        
    county_mech = 15.0
    county_prog_nei = 30.0
    county_policy = 15.0
    county_effect_nei = 10.0
    county_prog_wai = 20.0
    county_effect_wai = 10.0
    
    if len(scores) > 0:
        mech_sum = sum(s["mech"] for s in scores.values())
        if has_c:
            county_mech = (mech_sum + c_mech) / (len(scores) + 1)
        else:
            county_mech = mech_sum / len(scores)
            
        county_prog_nei = sum(s["prog_nei"] for s in scores.values()) / len(scores)
        county_policy = sum(s["policy"] for s in scores.values()) / len(scores)
        county_effect_nei = sum(s["effect_nei"] for s in scores.values()) / len(scores)
        county_prog_wai = sum(s["prog_wai"] for s in scores.values()) / len(scores)
        county_effect_wai = sum(s["effect_wai"] for s in scores.values()) / len(scores)
        
    county_avg = {
        "mech": county_mech,
        "prog_nei": county_prog_nei,
        "policy": county_policy,
        "effect_nei": county_effect_nei,
        "prog_wai": county_prog_wai,
        "effect_wai": county_effect_wai
    }
    deduct = (0.5 if req.special1 else 0.0) + (1.0 if req.special2 else 0.0) + req.special3
    final_score = round(county_mech, 1) + round(county_prog_nei, 1) + round(county_policy, 1) + round(county_effect_nei, 1) + round(county_prog_wai, 1) + round(county_effect_wai, 1) - deduct
    final_score = max(final_score, 0.0)
    
    url = await asyncio.to_thread(export_att11, county_avg, req.special1, req.special2, req.special3, final_score)
    return {"code": 200, "url": url}


# ================= 自查整改（附件12 / 附件13） =================

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

class LoginRequest(BaseModel):
    username: str
    password: str
    turnstile_token: Optional[str] = None

async def verify_turnstile_token(token: str, remote_ip: str = None) -> bool:
    """验证 Cloudflare Turnstile token"""
    if not token:
        return False
    cfg = load_config()
    secret_key = cfg.get("turnstile_secret_key", "0x4AAAAAABAhK4VmHHYq4mV3j4lAqm4vOtA")
    url = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
    data = {
        "secret": secret_key,
        "response": token
    }
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, data=data)
            result = resp.json()
            return bool(result.get("success", False))
    except Exception as e:
        print(f"Cloudflare Turnstile 验证请求失败: {e}")
        # 如果由于网络环境（如内网无法访问 Cloudflare 外网），记录日志并返回 False
        return False

@app.post("/api/auth/login")
async def api_login(req: LoginRequest):
    # 验证 Cloudflare Turnstile 人机验证码
    is_valid_turnstile = await verify_turnstile_token(req.turnstile_token)
    if not is_valid_turnstile:
        return {"code": 400, "message": "人机安全验证失败，请刷新重试"}

    token, err = await auth_module.login(req.username, req.password)
    if err:
        return {"code": 401, "message": err}
    perms = await auth_module.get_perms(req.username)
    payload = auth_module._verify_token(token)
    return {"code": 200, "token": token, "username": req.username,
            "role": payload.get("role","user"), "perms": perms}

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

class BatchCreateRequest(BaseModel):
    usernames: List[str]

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

@app.get("/api/auth/users")
async def api_list_users():
    users = await auth_module.list_users()
    return {"code": 200, "users": users}

@app.post("/api/auth/create_user")
async def api_create_user(req: CreateUserRequest):
    ok, err = await auth_module.create_user(req.username, req.role, req.password)
    if not ok:
        return {"code": 400, "message": err}
    return {"code": 200}

@app.post("/api/auth/batch_create")
async def api_batch_create(req: BatchCreateRequest):
    results = []
    for uname in req.usernames:
        uname = uname.strip()
        if not uname:
            continue
        ok, err = await auth_module.create_user(uname)
        results.append({"username": uname, "ok": ok, "err": err or ""})
    return {"code": 200, "results": results}

@app.post("/api/auth/delete_user")
async def api_delete_user(req: CreateUserRequest):
    ok, err = await auth_module.delete_user(req.username)
    if not ok:
        return {"code": 400, "message": err}
    return {"code": 200}

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

@app.post("/api/upload_evidence")
async def api_upload_evidence(file: UploadFile = File(...)):
    try:
        content = await file.read()
        filename = f"{uuid.uuid4().hex}.jpg"
        target_path = os.path.join(os.path.dirname(__file__), "uploads", filename)
        
        # 自动压缩与修正方向（针对手机高清拍照，限制长边最大1920px，质量85%）
        try:
            img = Image.open(io.BytesIO(content))
            img = ImageOps.exif_transpose(img) # 纠正手机拍照旋转角度
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # 长边超过 1920 时按比例等比缩放
            max_size = 1920
            if max(img.size) > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            img.save(target_path, "JPEG", quality=85, optimize=True)
        except Exception:
            # 如非标准图像格式直接保存原二进制
            with open(target_path, "wb") as f:
                f.write(content)
                
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

class InquirySaveRequest(BaseModel):
    cbfbm: str
    township_name: str
    village_name: str
    group_name: str
    cbfmc: str
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
    
    for sign_key in ['bxwrqm', 'xwrqm', 'cmdbqm']:
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

    async with SessionLocal() as session:
        res = await session.execute(text("SELECT id FROM waiye_inquiries WHERE cbfbm = :cbfbm LIMIT 1"), {"cbfbm": req.cbfbm})
        row = res.fetchone()
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
            """), {"cbfbm": req.cbfbm, "t": req.township_name, "v": req.village_name, "g": req.group_name, "m": req.cbfmc, "form_data": json.dumps(req.form_data)})
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

@app.post("/api/export_waiye_inquiry")
async def api_export_waiye_inquiry(req: ExportInquiryRequest):
    from database import SessionLocal
    from sqlalchemy import text
    async with SessionLocal() as session:
        res = await session.execute(text("SELECT * FROM waiye_inquiries WHERE cbfbm = :cbfbm"), {"cbfbm": req.cbfbm})
        row = res.fetchone()
        if not row:
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
        real_cbfmc = samp_row[0] if (samp_row and samp_row[0]) else (row[5] or "")
        
        fd = row[6] or {}
        bxwr_name = fd.get("bxwr") or fd.get("cbfmc") or real_cbfmc
        data = {
            "cbfbm": req.cbfbm,
            "cbfmc": real_cbfmc,
            "bxwr": bxwr_name,
            "township_name": row[2] or "",
            "village_name": row[3] or "",
            "group_name": row[4] or "",
            "lxdh": fd.get("lxdh", lxdh),
            "gender": fd.get("gender", gender),
            "dk_cnt": dk_cnt,
            "scmj": ht_mj,
            "form_data": fd
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
