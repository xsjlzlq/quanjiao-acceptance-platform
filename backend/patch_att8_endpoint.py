with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", "r", encoding="utf-8") as f:
    code = f.read()

# Replace ExportWaiyeAtt8Request and api_export_waiye_att8
old_start = code.find("class ExportWaiyeAtt8Request(BaseModel):")
old_end = code.find("@app.get(\"/api/export_waiye_att9\")")

new_block = """class ExportWaiyeAtt8Request(BaseModel):
    township_name: str
    village_name: Optional[str] = None
    group_name: Optional[str] = None
    group_code: Optional[str] = None

@app.post("/api/export_waiye_att8")
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

"""

code = code[:old_start] + new_block + code[old_end:]

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", "w", encoding="utf-8") as f:
    f.write(code)

import py_compile
py_compile.compile(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", doraise=True)
print("api_export_waiye_att8 patched successfully!")