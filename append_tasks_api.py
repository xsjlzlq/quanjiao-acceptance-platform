import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

api_code = """
import random
import pandas as pd
from typing import Optional
from fastapi.responses import FileResponse
import os

@app.get("/api/hierarchy")
async def get_hierarchy():
    from database import SessionLocal
    async with SessionLocal() as session:
        result = await session.execute(text("SELECT qsdwdm, qsdwmc FROM qsdwdmb ORDER BY qsdwdm"))
        rows = result.fetchall()
        
        townships = []
        villages = []
        groups = []
        
        for r in rows:
            code = r[0]
            name = r[1]
            if code.endswith('00000') and not code.endswith('00000000'):
                townships.append({"code": code[:9], "name": name, "full_code": code})
            elif code.endswith('00') and not code.endswith('00000'):
                villages.append({"code": code[:12], "name": name, "full_code": code, "parent": code[:9]})
            elif not code.endswith('00'):
                groups.append({"code": code, "name": name, "full_code": code, "parent": code[:12]})
                
        return {"code": 200, "townships": townships, "villages": villages, "groups": groups}

@app.get("/api/contractor_count")
async def get_contractor_count(group_code: str):
    from database import SessionLocal
    async with SessionLocal() as session:
        sql = text("SELECT COUNT(*) FROM cbf WHERE cbfbm LIKE :code")
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

@app.post("/api/sample")
async def do_sample(req: SampleRequest):
    from database import SessionLocal
    async with SessionLocal() as session:
        sampled_groups = []
        if req.mode == 1:
            sampled_groups.append({"code": req.group_code, "name": req.group_name, "v_name": req.village_name})
        elif req.mode == 2:
            sql = text("SELECT qsdwdm, qsdwmc FROM qsdwdmb WHERE qsdwdm LIKE :ts AND qsdwdm NOT LIKE '%00'")
            res = await session.execute(sql, {"ts": f"{req.township_code}%"})
            all_groups = res.fetchall()
            
            if not all_groups:
                return {"code": 400, "message": "该镇下无村民组"}
            k = random.randint(2, min(5, max(2, len(all_groups))))
            if len(all_groups) < 2:
                k = len(all_groups)
            picked = random.sample(all_groups, k)
            
            for g in picked:
                v_code = g[0][:12] + "00"
                v_res = await session.execute(text("SELECT qsdwmc FROM qsdwdmb WHERE qsdwdm = :vc"), {"vc": v_code})
                v_name = v_res.scalar() or v_code
                sampled_groups.append({"code": g[0], "name": g[1], "v_name": v_name})
        
        stats = []
        out_att8_data = []
        
        os.makedirs("downloads", exist_ok=True)
        
        for g in sampled_groups:
            g_code = g["code"]
            sql = text("SELECT cbfbm, cbfmc, lxdh FROM cbf WHERE cbfbm LIKE :code")
            res = await session.execute(sql, {"code": f"{g_code}%"})
            cbfs = res.fetchall()
            total_cbf = len(cbfs)
            sample_size = max(1, int(total_cbf * 0.05)) if total_cbf > 0 else 0
            
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
                
                for idx, c in enumerate(sampled):
                    sql_dk = text('''
                        SELECT a.dkbm, a.dkmc, a.scmj, a.dkdz, a.dkxz, a.dknz, a.dkbz 
                        FROM dkxx_shp_attrs a
                        JOIN cbdkxx b ON a.dkbm = b.dkbm
                        WHERE b.cbfbm = :cbfbm
                    ''')
                    res_dk = await session.execute(sql_dk, {"cbfbm": c[0]})
                    dks = res_dk.fetchall()
                    if not dks:
                        out_att8_data.append({
                            "序号": len(out_att8_data) + 1,
                            "乡镇": req.township_name,
                            "行政村": g["v_name"],
                            "村民小组": g["name"],
                            "承包方代表": c[1],
                            "承包方编码(缩略码)": c[0],
                            "联系电话": c[2] or '',
                            "地块名称": "",
                            "地块简编码": "",
                            "成果面积(亩)": "",
                            "是否认可确权面积": "",
                            "权属调查结果是否正确": "",
                            "地块四至是否正确": "",
                            "家庭成员是否本经济组织成员": "",
                            "是否本人核实地块": "",
                            "是否本人签名确认": "",
                            "是否满意": "",
                            "调查抽样方式": "",
                            "承包方代表签名": ""
                        })
                    for dk in dks:
                        out_att8_data.append({
                            "序号": len(out_att8_data) + 1,
                            "乡镇": req.township_name,
                            "行政村": g["v_name"],
                            "村民小组": g["name"],
                            "承包方代表": c[1],
                            "承包方编码(缩略码)": c[0],
                            "联系电话": c[2] or '',
                            "地块名称": dk[1],
                            "地块简编码": dk[0],
                            "成果面积(亩)": dk[2],
                            "是否认可确权面积": "",
                            "权属调查结果是否正确": "",
                            "地块四至是否正确": "",
                            "家庭成员是否本经济组织成员": "",
                            "是否本人核实地块": "",
                            "是否本人签名确认": "",
                            "是否满意": "",
                            "调查抽样方式": "",
                            "承包方代表签名": ""
                        })
                        
        df_stats = pd.DataFrame(stats)
        att5_path = f"downloads/附件5_抽样统计表_{req.township_code}.xlsx"
        df_stats.to_excel(att5_path, index=False)
        
        df_att8 = pd.DataFrame(out_att8_data)
        att8_path = f"downloads/附件8_外业核查记录表_{req.township_code}.xlsx"
        df_att8.to_excel(att8_path, index=False)
        
        return {
            "code": 200, 
            "message": "抽样成功",
            "stats": stats,
            "att5_url": f"/api/download?file={att5_path}",
            "att8_url": f"/api/download?file={att8_path}"
        }

@app.get("/api/download")
async def download_file(file: str):
    if os.path.exists(file):
        return FileResponse(file, filename=os.path.basename(file))
    return {"code": 404, "message": "File not found"}

@app.get("/api/generate_att4")
async def generate_att4():
    os.makedirs("downloads", exist_ok=True)
    path = "downloads/附件4_成果检查验收申请表.xlsx"
    df = pd.DataFrame([
        {"申请单位": "", "主要负责人及职务": "", "联系电话": "", "联系人及职务": "", "联系电话2": ""},
        {"承包起止时间": "", "网签平台": "", "农户总数(户)": "", "延包合同签订数(份)": "", "确权总面积(亩)": ""},
        {"延包合同面积(亩)": "", "暂缓延包农户数(户)": "", "暂缓延包面积(亩)": "", "县级意见": ""}
    ])
    df.to_excel(path, index=False)
    return {"code": 200, "url": f"/api/download?file={path}"}
"""

with open('backend/main.py', 'a', encoding='utf-8') as f:
    f.write(api_code)
print("Backend updated.")
