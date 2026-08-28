import asyncio
from database import engine
from sqlalchemy import text

async def check_all():
    async with engine.begin() as conn:
        res = await conn.execute(text("SELECT COUNT(*) FROM waiye_samples"))
        print(f"waiye_samples count: {res.scalar()}")
        
        res2 = await conn.execute(text("SELECT township_name, village_name, group_name, count(*) FROM waiye_samples GROUP BY township_name, village_name, group_name"))
        rows = res2.fetchall()
        print(f"waiye_samples groups ({len(rows)}):")
        for r in rows:
            print(f"  {r[0]} - {r[1]} - {r[2]}: {r[3]} records")

        res_cbf = await conn.execute(text("SELECT COUNT(*) FROM cbf"))
        print(f"cbf table count: {res_cbf.scalar()}")

        res_dk = await conn.execute(text("SELECT COUNT(*) FROM cbdkxx"))
        print(f"cbdkxx table count: {res_dk.scalar()}")

asyncio.run(check_all())