with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", "r", encoding="utf-8") as f:
    code = f.read()

clear_endpoint = """

class SampleClearRequest(BaseModel):
    township_code: Optional[str] = None
    township_name: Optional[str] = None
    group_code: Optional[str] = None

@app.post("/api/sample/clear")
async def clear_samples(req: Optional[SampleClearRequest] = None):
    async with SessionLocal() as session:
        if req and req.group_code:
            sql = text("DELETE FROM waiye_samples WHERE group_code = :gc")
            await session.execute(sql, {"gc": req.group_code})
        elif req and req.township_name:
            sql = text("DELETE FROM waiye_samples WHERE township_name = :tn")
            await session.execute(sql, {"tn": req.township_name})
        elif req and req.township_code:
            sql = text("DELETE FROM waiye_samples WHERE group_code LIKE :tc")
            await session.execute(sql, {"tc": f"{req.township_code}%"})
        else:
            sql = text("DELETE FROM waiye_samples")
            await session.execute(sql)
            
        await session.commit()
        return {"code": 200, "message": "抽样数据已成功清空"}
"""

if "/api/sample/clear" not in code:
    # Insert before # ================= 内业核查 API =================
    pos = code.find("# ================= 内业核查 API =================")
    if pos != -1:
        code = code[:pos] + clear_endpoint + "\n" + code[pos:]
    else:
        code += "\n" + clear_endpoint

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", "w", encoding="utf-8") as f:
    f.write(code)

import py_compile
py_compile.compile(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", doraise=True)
print("clear_samples endpoint added successfully!")