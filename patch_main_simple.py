import sys
import re

with open('backend/main.py', 'r', encoding='utf-8') as f:
    code = f.read()

new_block = """@app.post("/api/sample")
async def do_sample(req: SampleRequest):
    from database import SessionLocal
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
        out_att8_data = []
        
        for g in sampled_groups:
            g_code = str(g["code"])
            sql = text("SELECT cbfbm, cbfmc, lxdh FROM cbf WHERE cbfbm::text LIKE :code")
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
                        SELECT b.dkbm, a.dkmc, b.htmjm 
                        FROM cbdkxx b
                        LEFT JOIN dkxx_shp_attrs a ON a.dkbm = b.dkbm
                        WHERE b.cbfbm::text = :cbfbm
                    ''')
                    res_dk = await session.execute(sql_dk, {"cbfbm": c[0]})
                    dks = res_dk.fetchall()
                    if not dks:
                        out_att8_data.append({
                            "乡镇": req.township_name,
                            "行政村": g["v_name"],
                            "村民小组": g["name"],
                            "承包方代表": c[1],
                            "承包方编码(缩略码)": str(c[0])[-4:] if c[0] else "",
                            "联系电话": str(c[2]) if c[2] else "",
                            "地块名称": "",
                            "地块简编码": "",
                            "成果面积(亩)": ""
                        })
                    for dk in dks:
                        out_att8_data.append({
                            "乡镇": req.township_name,
                            "行政村": g["v_name"],
                            "村民小组": g["name"],
                            "承包方代表": c[1],
                            "承包方编码(缩略码)": str(c[0])[-4:] if c[0] else "",
                            "联系电话": str(c[2]) if c[2] else "",
                            "地块名称": dk[1],
                            "地块简编码": str(dk[0])[-5:] if dk[0] else "",
                            "成果面积(亩)": dk[2]
                        })
                        
        import asyncio
        urls = await asyncio.to_thread(export_docs, stats, out_att8_data, req.township_code, req.township_name)
        
        return {
            "code": 200, 
            "message": "抽样成功",
            "stats": stats,
            "urls": urls
        }

@app.get("/api/download")
async def download_file(file: str):
    if os.path.exists(file):
        from fastapi.responses import FileResponse
        return FileResponse(file, filename=os.path.basename(file))
    return {"code": 404, "message": "File not found"}

@app.get("/api/generate_att4")
async def generate_att4(township_name: str = "默认乡镇"):
    import asyncio
    url = await asyncio.to_thread(export_att4, township_name)
    return {"code": 200, "url": url}
"""

new_code = re.sub(r'@app.post\("/api/sample"\).*?def generate_att4.*?return.*?\}', new_block, code, flags=re.DOTALL)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(new_code)
print("Regex replaced")
