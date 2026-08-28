import asyncio
from database import engine
from sqlalchemy import text
import requests

# 1. Insert mock sample records for 2 townships: 襄河镇 and 古河镇
async def setup_mock_samples():
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM waiye_samples"))
        await conn.execute(text("""
            INSERT INTO waiye_samples (
                township_name, village_name, group_name, group_code,
                cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm, dkbm_short, scmj
            ) VALUES 
            ('襄河镇', '邱塔村', '第一组', '341124100200001', '张三', '3411241002000010001', '0001', '1380001', '地块1', '001', '01', 2.5),
            ('襄河镇', '邱塔村', '第二组', '341124100200002', '李四', '3411241002000020001', '0002', '1380002', '地块2', '002', '02', 3.0),
            ('古河镇', '古河村', '第一组', '341124101200001', '王五', '3411241012000010001', '0003', '1380003', '地块3', '003', '03', 1.8),
            ('古河镇', '古河村', '第二组', '341124101200002', '赵六', '3411241012000020001', '0004', '1380004', '地块4', '004', '04', 4.1)
        """))

asyncio.run(setup_mock_samples())

# Check hierarchy
r_h1 = requests.get('http://127.0.0.1:8081/api/waiye/hierarchy').json()
ts_list = [x['text'] for x in r_h1.get('tree', [])]
print("Initial Townships in Waiye samples:", ts_list, "total groups:", r_h1.get('total_groups'))

# Clear ONLY 襄河镇
r_clear_ts = requests.post('http://127.0.0.1:8081/api/sample/clear', json={
    'level': 'township',
    'township_code': '341124100',
    'township_name': '襄河镇'
}).json()
print("Clear 襄河镇 response:", r_clear_ts)

# Check hierarchy after clearing 襄河镇 -> 古河镇 should still be there!
r_h2 = requests.get('http://127.0.0.1:8081/api/waiye/hierarchy').json()
ts_list2 = [x['text'] for x in r_h2.get('tree', [])]
print("Townships after clearing 襄河镇:", ts_list2, "total groups:", r_h2.get('total_groups'))

# Clear County (ALL)
r_clear_county = requests.post('http://127.0.0.1:8081/api/sample/clear', json={
    'level': 'county'
}).json()
print("Clear County response:", r_clear_county)

# Check hierarchy after clearing County -> should be 0 groups
r_h3 = requests.get('http://127.0.0.1:8081/api/waiye/hierarchy').json()
print("Townships after clearing County:", r_h3.get('tree', []), "total groups:", r_h3.get('total_groups'))