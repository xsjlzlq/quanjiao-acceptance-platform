import asyncio
from database import engine
from sqlalchemy import text
import json
async def test():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("INSERT INTO neiye_records (qsdwdm, form_data) VALUES ('test', :fd) ON CONFLICT (qsdwdm) DO UPDATE SET form_data=EXCLUDED.form_data"), {'fd': json.dumps({'a':1})})
            print('ok')
        except Exception as e:
            print('err:', e)
asyncio.run(test())