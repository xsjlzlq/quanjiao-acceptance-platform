import sys

with open('backend/main.py', 'r', encoding='utf-8') as f:
    code = f.read()

excel_endpoint = """
from fastapi import UploadFile, File

@app.post("/api/sample_by_excel")
async def do_sample_by_excel(file: UploadFile = File(...)):
    import pandas as pd
    import math
    import random
    from database import SessionLocal
    
    os.makedirs("uploads/抽样表", exist_ok=True)
    file_path = os.path.join("uploads/抽样表", file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
        
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
        out_att8_data = []
        
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
                        out_att8_data.append({
                            "乡镇": g_town,
                            "行政村": g_vill,
                            "村民小组": g_name,
                            "承包方代表": c[1],
                            "承包方编码(缩略码)": str(c[0])[-4:] if c[0] else "",
                            "联系电话": str(c[2]) if c[2] else "",
                            "地块名称": "",
                            "地块简编码": "",
                            "成果面积(亩)": ""
                        })
                    for dk in dks:
                        out_att8_data.append({
                            "乡镇": g_town,
                            "行政村": g_vill,
                            "村民小组": g_name,
                            "承包方代表": c[1],
                            "承包方编码(缩略码)": str(c[0])[-4:] if c[0] else "",
                            "联系电话": str(c[2]) if c[2] else "",
                            "地块名称": dk[1],
                            "地块简编码": str(dk[0])[-5:] if dk[0] else "",
                            "成果面积(亩)": dk[2]
                        })
        
        import asyncio
        urls = await asyncio.to_thread(export_docs, stats, out_att8_data, township_code, township_name)
        
        return {
            "code": 200, 
            "message": "抽样成功",
            "stats": stats,
            "urls": urls
        }
"""

with open('backend/main.py', 'a', encoding='utf-8') as f:
    f.write(excel_endpoint)

print("main.py appended.")
