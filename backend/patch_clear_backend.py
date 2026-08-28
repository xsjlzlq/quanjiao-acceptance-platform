with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", "r", encoding="utf-8") as f:
    code = f.read()

old_start = code.find("class SampleClearRequest(BaseModel):")
old_end = code.find("# ================= 内业核查 API =================")

new_clear_block = """class SampleClearRequest(BaseModel):
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

"""

code = code[:old_start] + new_clear_block + code[old_end:]

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", "w", encoding="utf-8") as f:
    f.write(code)

import py_compile
py_compile.compile(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", doraise=True)
print("main.py clear_samples updated and compiled successfully.")