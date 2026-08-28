import asyncio
from database import engine
from sqlalchemy import text

async def test_waiye_data_flow():
    async with engine.begin() as conn:
        # Clear test samples
        await conn.execute(text("DELETE FROM waiye_samples WHERE township_name = '测试乡镇'"))
        
        # Insert sample
        sql_insert = text("""
            INSERT INTO waiye_samples (
                township_name, village_name, group_name, group_code,
                cbfmc, cbfbm, cbfbm_short, lxdh,
                dkmc, dkbm, dkbm_short, scmj
            ) VALUES (
                '测试乡镇', '测试村', '第一组', '341124100200001',
                '张三', '3411241002000010001', '0001', '13800138000',
                '大田', '3411241002000010001001', '001', 3.5
            ), (
                '测试乡镇', '测试村', '第一组', '341124100200001',
                '李四', '3411241002000010002', '0002', '13800138001',
                '西田', '3411241002000010002001', '002', 4.2
            )
        """)
        await conn.execute(sql_insert)
        
        # Test hierarchy query
        sql_hier = text("""
            SELECT DISTINCT township_name, village_name, group_name, group_code, COUNT(*) as cnt
            FROM waiye_samples
            GROUP BY township_name, village_name, group_name, group_code
            ORDER BY township_name, village_name, group_name
        """)
        res = await conn.execute(sql_hier)
        rows = res.fetchall()
        print("Sampled groups in DB:")
        for r in rows:
            print(f"  {r[0]} > {r[1]} > {r[2]} ({r[3]}): {r[4]} records")

asyncio.run(test_waiye_data_flow())