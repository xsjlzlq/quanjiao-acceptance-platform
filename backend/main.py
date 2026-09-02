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
from sqlalchemy import text
from database import SessionLocal
from data_importer import import_data_from_path
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

@app.post("/api/import-data")
async def api_import_data(req: ImportRequest):
    path = req.source_path
    if not os.path.exists(path):
        return {"code": 404, "message": f"找不到指定的数据包路径: {path}"}
    try:
        success = await import_data_from_path(path)
        if success:
            return {"code": 200, "message": "全量数据包入库成功！"}
        else:
            return {"code": 500, "message": "入库执行失败，请检查数据包格式。"}
    except Exception as e:
        return {"code": 500, "message": f"服务器异常: {str(e)}"}

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
        sql = text("SELECT cbfbm, cbfmc, lxdh FROM cbf WHERE cbfbm::text LIKE :code")
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

@app.post("/api/sample")
async def do_sample(req: SampleRequest):
    async with SessionLocal() as session:
        sampled_groups = []
        if req.mode == 1:
            sampled_groups.append({"code": req.group_code, "name": req.group_name, "v_name": req.village_name})
        elif req.mode == 2:
            sql = text("SELECT qsdwdm, qsdwmc FROM qsdwdmb WHERE qsdwdm::text LIKE :ts AND qsdwdm::text NOT LIKE '%00'")
            res = await session.execute(sql, {"ts": f"{req.township_code}%"})
            all_groups = res.fetchall()
            
            if not all_groups:
                return {"code": 400, "message": "该镇下无村民组"}
            k = random.randint(2, min(5, max(2, len(all_groups))))
            if len(all_groups) < 2:
                k = len(all_groups)
            picked = random.sample(all_groups, k)
            
            for g in picked:
                v_code = str(g[0])[:12] + "00"
                v_res = await session.execute(text("SELECT qsdwmc FROM qsdwdmb WHERE qsdwdm::text = :vc"), {"vc": v_code})
                v_name = v_res.scalar() or v_code
                sampled_groups.append({"code": g[0], "name": g[1], "v_name": v_name})
        
        stats = []
        
        for g in sampled_groups:
            g_code = str(g["code"])
            sql = text("SELECT cbfbm, cbfmc, lxdh FROM cbf WHERE cbfbm::text LIKE :code")
            res = await session.execute(sql, {"code": f"{g_code}%"})
            cbfs = res.fetchall()
            total_cbf = len(cbfs)
            
            if req.mode == 1 and req.manual_sample_count is not None and req.manual_sample_count > 0:
                sample_size = min(total_cbf, req.manual_sample_count)
            else:
                sample_size = math.ceil(total_cbf * 0.05) if total_cbf > 0 else 0
            
            if sample_size > 0:
                sampled = random.sample(cbfs, sample_size)
                stats.append({
                    "序号": len(stats) + 1,
                    "乡镇名称": req.township_name,
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
                            "t_name": req.township_name, "v_name": g["v_name"], "g_name": g["name"], "g_code": g_code,
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
                            "t_name": req.township_name, "v_name": g["v_name"], "g_name": g["name"], "g_code": g_code,
                            "cbfmc": c[1], "cbfbm": str(c[0]), "cbfbm_short": str(c[0])[-4:] if c[0] else "",
                            "lxdh": str(c[2]) if c[2] else "",
                            "dkmc": dk[1] or "",
                            "dkbm": str(dk[0]) if dk[0] else "",
                            "dkbm_short": str(dk[0])[-5:] if dk[0] else "",
                            "scmj": float(dk[2]) if dk[2] is not None else 0.0
                        })
                        
        await session.commit()
        url_att5 = await asyncio.to_thread(export_att5, stats, req.township_code, req.township_name)
        
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
    if os.path.exists(file):
        from fastapi.responses import FileResponse
        return FileResponse(file, filename=os.path.basename(file))
    return {"code": 404, "message": "File not found"}

@app.get("/api/generate_att4")
async def generate_att4(township_name: str = "默认乡镇", township_code: str = ""):
    from database import SessionLocal
    from sqlalchemy import text
    async with SessionLocal() as session:
        if township_code:
            code_prefix = township_code
        else:
            r = await session.execute(text("SELECT qsdwdm FROM qsdwdmb WHERE qsdwmc = :name"), {"name": township_name})
            code_prefix = r.scalar() or "341124"
        
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
        stats = []
        
        township_name = str(df.iloc[0]["乡镇名"]) if not df.empty else "默认乡镇"
        township_code = str(df.iloc[0]["发包方编码"])[:9] if not df.empty else "000"
        
        for idx, row in df.iterrows():
            g_code = str(row["发包方编码"]).strip()
            if g_code.endswith('.0'): g_code = g_code[:-2]
            g_town = str(row["乡镇名"]).strip()
            g_vill = str(row["村名"]).strip()
            g_name = str(row["组名"]).strip()
            
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
            
            if sample_count is not None and sample_count > 0:
                sample_size = min(total_cbf, sample_count)
            else:
                sample_size = math.ceil(total_cbf * 0.05) if total_cbf > 0 else 0
                
            if sample_size > 0:
                sampled = random.sample(cbfs, sample_size)
                stats.append({
                    "序号": len(stats) + 1,
                    "乡镇名称": g_town,
                    "村名称": g_vill, 
                    "组名称": g_name,
                    "发包方总户数": total_cbf,
                    "抽样农户数5%": sample_size
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
            SELECT township_name, village_name, group_name, group_code, COUNT(*) as sample_count
            FROM waiye_samples
            GROUP BY township_name, village_name, group_name, group_code
            ORDER BY township_name, village_name, group_name
        """)
        res = await session.execute(sql)
        rows = res.fetchall()
        
        township_map = {}
        for r in rows:
            t_name, v_name, g_name, g_code, cnt = r[0], r[1], r[2], r[3], r[4]
            if t_name not in township_map:
                township_map[t_name] = {}
            if v_name not in township_map[t_name]:
                township_map[t_name][v_name] = []
            township_map[t_name][v_name].append({
                "name": g_name,
                "code": g_code,
                "count": cnt
            })
            
        tree = []
        for t_name, v_dict in township_map.items():
            v_children = []
            for v_name, g_list in v_dict.items():
                g_children = [
                    {
                        "text": f"{g['name']} ({g['count']}条)",
                        "value": g["code"],
                        "group_name": g["name"],
                        "group_code": g["code"],
                        "village_name": v_name,
                        "township_name": t_name,
                        "count": g["count"]
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
        r = await session.execute(text("SELECT form_data FROM neiye_records WHERE qsdwdm = '341124'"))
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
        r = await session.execute(text("SELECT form_data FROM neiye_records WHERE qsdwdm = '341124'"))
        row = r.fetchone()
        fd = row[0] if (row and row[0]) else {}
        fd["special1"] = req.special1
        fd["special2"] = req.special2
        fd["special3"] = req.special3
        
        sql = text('''
            INSERT INTO neiye_records (qsdwdm, qsdwmc, level, form_data, score, updated_at)
            VALUES ('341124', '全椒县', 'county', :fd, 0, CURRENT_TIMESTAMP)
            ON CONFLICT (qsdwdm) DO UPDATE SET
                form_data = EXCLUDED.form_data,
                updated_at = CURRENT_TIMESTAMP
        ''')
        await session.execute(sql, {"fd": json.dumps(fd)})
        await session.commit()
    return {"code": 200, "message": "保存成功"}

# ================= 认证 & 用户管理 API =================

class LoginRequest(BaseModel):
    username: str
    password: str

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

@app.post("/api/auth/login")
async def api_login(req: LoginRequest):
    token, err = await auth_module.login(req.username, req.password)
    if err:
        return {"code": 401, "message": err}
    perms = await auth_module.get_perms(req.username)
    payload = auth_module._verify_token(token)
    return {"code": 200, "token": token, "username": req.username,
            "role": payload.get("role","user"), "perms": perms}

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
        
        fd = row[6] or {}
        data = {
            "cbfbm": req.cbfbm,
            "cbfmc": fd.get("cbfmc", row[5] or ""),
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
