with open(r'G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Update import on top
if 'export_waiye_att9' not in code:
    code = code.replace(
        'export_waiye_att8,',
        'export_waiye_att8, export_waiye_att9,'
    )

api_additions = """

@app.get("/api/export_waiye_att9")
async def api_export_waiye_att9():
    from database import SessionLocal
    from sqlalchemy import text
    async with SessionLocal() as session:
        sql = text(\"\"\"
            SELECT id, township_name, village_name, group_name,
                   cbfmc, cbfbm_short, lxdh, dkmc, dkbm_short, scmj,
                   area_acknowledged, rights_correct, bound_correct, member_qualified,
                   self_verified, self_signed, satisfaction, survey_method
            FROM waiye_samples
            ORDER BY township_name, village_name, group_name, id
        \"\"\")
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
                "cbfbm_short": r[5],
                "lxdh": r[6],
                "dkmc": r[7],
                "dkbm_short": r[8],
                "scmj": float(r[9]) if r[9] is not None else 0.0,
                "area_acknowledged": r[10] or "",
                "rights_correct": r[11] or "",
                "bound_correct": r[12] or "",
                "member_qualified": r[13] or "",
                "self_verified": r[14] or "",
                "self_signed": r[15] or "",
                "satisfaction": r[16] or "满意",
                "survey_method": r[17] or "现场"
            })
            
    url = await asyncio.to_thread(export_waiye_att9, samples_rows)
    return {"code": 200, "url": url}

@app.get("/api/waiye/townships_summary")
async def get_waiye_townships_summary():
    from database import SessionLocal
    from sqlalchemy import text
    async with SessionLocal() as session:
        sql = text(\"\"\"
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
        \"\"\")
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
"""

if '/api/export_waiye_att9' not in code:
    code += '\n' + api_additions

with open(r'G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py', 'w', encoding='utf-8') as f:
    f.write(code)

import py_compile
py_compile.compile(r'G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py', doraise=True)
print('main.py updated successfully.')