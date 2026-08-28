import asyncio
from database import engine
from sqlalchemy import text

async def test_db():
    async with engine.begin() as conn:
        tables = ["qsdwdmb", "cbf", "cbdkxx", "dkxx_shp_attrs", "waiye_samples", "neiye_records", "contractor_signatures"]
        for t in tables:
            try:
                res = await conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
                cnt = res.scalar()
                print(f"Table {t}: {cnt} rows")
            except Exception as e:
                print(f"Table {t}: ERROR {e}")

asyncio.run(test_db())