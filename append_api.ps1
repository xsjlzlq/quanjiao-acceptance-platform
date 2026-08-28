$apiCode = @"

# ==========================================
# 核心业务接口：外业核查
# ==========================================
from sqlalchemy import text

@app.get("/api/villages")
async def get_villages():
    from database import SessionLocal
    async with SessionLocal() as session:
        result = await session.execute(text("SELECT qsdwdm, qsdwmc FROM qsdwdmb ORDER BY qsdwdm"))
        rows = result.fetchall()
        data = [{"code": r[0], "name": r[1]} for r in rows if r[0] and not r[0].endswith('00')]
        return {"code": 200, "data": data}

@app.get("/api/contractors")
async def get_contractors(qsdwdm: str):
    from database import SessionLocal
    async with SessionLocal() as session:
        sql = text("SELECT cbfbm, cbfmc, lxdh FROM cbf WHERE cbfbm LIKE :code")
        result = await session.execute(sql, {"code": f"{qsdwdm}%"})
        rows = result.fetchall()
        data = [{"cbfbm": r[0], "cbfmc": r[1], "lxdh": r[2]} for r in rows]
        return {"code": 200, "data": data}

@app.get("/api/parcels")
async def get_parcels(cbfbm: str):
    from database import SessionLocal
    async with SessionLocal() as session:
        sql = text("""
            SELECT a.dkbm, a.dkmc, a.scmj, a.dkdz, a.dkxz, a.dknz, a.dkbz 
            FROM dkxx_shp_attrs a
            JOIN cbdkxx b ON a.dkbm = b.dkbm
            WHERE b.cbfbm = :cbfbm
        """)
        result = await session.execute(sql, {"cbfbm": cbfbm})
        rows = result.fetchall()
        data = [{
            "dkbm": r[0], "dkmc": r[1], "scmj": r[2],
            "dkdz": r[3], "dkxz": r[4], "dknz": r[5], "dkbz": r[6]
        } for r in rows]
        return {"code": 200, "data": data}
"@
Add-Content -Path backend/main.py -Value $apiCode -Encoding UTF8
