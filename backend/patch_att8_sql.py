with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace SELECT queries in api_export_waiye_att8
old_block = """@app.post("/api/export_waiye_att8")
async def api_export_waiye_att8(req: ExportWaiyeAtt8Request):
    async with SessionLocal() as session:
        if req.group_code:
            sql = text(\"\"\"
                SELECT id, township_name, village_name, group_name,
                       cbfmc, cbfbm_short, lxdh, dkmc, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method
                FROM waiye_samples
                WHERE group_code = :gc
                ORDER BY id
            \"\"\")
            res = await session.execute(sql, {"gc": req.group_code})
        elif req.village_name and req.group_name:
            sql = text(\"\"\"
                SELECT id, township_name, village_name, group_name,
                       cbfmc, cbfbm_short, lxdh, dkmc, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method
                FROM waiye_samples
                WHERE township_name = :tn AND village_name = :vn AND group_name = :gn
                ORDER BY id
            \"\"\")
            res = await session.execute(sql, {"tn": req.township_name, "vn": req.village_name, "gn": req.group_name})
        else:
            sql = text(\"\"\"
                SELECT id, township_name, village_name, group_name,
                       cbfmc, cbfbm_short, lxdh, dkmc, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method
                FROM waiye_samples
                WHERE township_name = :tn
                ORDER BY village_name, group_name, id
            \"\"\")
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
                "cbfbm": str(r[0]) if False else (r[0] if False else str(r[0])), # query col 5 is cbfbm
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
            })"""

new_block = """@app.post("/api/export_waiye_att8")
async def api_export_waiye_att8(req: ExportWaiyeAtt8Request):
    async with SessionLocal() as session:
        if req.group_code:
            sql = text(\"\"\"
                SELECT id, township_name, village_name, group_name,
                       cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method, signature_url
                FROM waiye_samples
                WHERE group_code = :gc
                ORDER BY cbfbm, id
            \"\"\")
            res = await session.execute(sql, {"gc": req.group_code})
        elif req.village_name and req.group_name:
            sql = text(\"\"\"
                SELECT id, township_name, village_name, group_name,
                       cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method, signature_url
                FROM waiye_samples
                WHERE township_name = :tn AND village_name = :vn AND group_name = :gn
                ORDER BY cbfbm, id
            \"\"\")
            res = await session.execute(sql, {"tn": req.township_name, "vn": req.village_name, "gn": req.group_name})
        else:
            sql = text(\"\"\"
                SELECT id, township_name, village_name, group_name,
                       cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method, signature_url
                FROM waiye_samples
                WHERE township_name = :tn
                ORDER BY village_name, group_name, cbfbm, id
            \"\"\")
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
                "signature_url": r[19] or ""
            })"""

code = code.replace(old_block, new_block)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", "w", encoding="utf-8") as f:
    f.write(code)

import py_compile
py_compile.compile(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", doraise=True)
print("api_export_waiye_att8 correctly updated with cbfbm and signature_url.")