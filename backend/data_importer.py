# -*- coding: utf-8 -*-
import os
import pyodbc
import pandas as pd
import geopandas as gpd
from sqlalchemy import create_engine
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DATABASE_URL_SYNC = "postgresql://postgres:123456@localhost:5432/quanjiao"

def import_data_from_path(source_dir: str):
    engine = create_engine(DATABASE_URL_SYNC)
    mdb_path = os.path.join(source_dir, r'权属数据\341124100.mdb')
    shp_path = os.path.join(source_dir, r'矢量数据\DK341124100.shp')
    xls_path = os.path.join(source_dir, r'权属数据\3411242026权属单位代码表.xls')
    
    log = []
    print('正在导入 SHP 属性数据...')
    try:
        if not os.path.exists(shp_path):
            raise FileNotFoundError(shp_path)
        gdf = gpd.read_file(shp_path)
        df_shp = pd.DataFrame(gdf.drop(columns='geometry'))
        df_shp.columns = [c.lower() for c in df_shp.columns]
        if 'id' not in df_shp.columns:
            df_shp.insert(0, 'id', range(1, 1 + len(df_shp)))
        df_shp.to_sql('dkxx_shp_attrs', engine, if_exists='replace', index=False, chunksize=1000)
        log.append('SHP 属性数据导入成功')
    except Exception as e:
        log.append(f'SHP 导入失败: {e}')
        
    print('正在导入 MDB 权属数据...')
    try:
        if not os.path.exists(mdb_path):
            raise FileNotFoundError(mdb_path)
        conn_str = r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};DBQ=' + mdb_path + ';'
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            tables = [table.table_name for table in cursor.tables(tableType='TABLE')]
            for table in tables:
                if table.startswith('~'): continue
                df = pd.read_sql(f'SELECT * FROM [{table}]', conn)
                df.columns = [c.lower() for c in df.columns]
                df.to_sql(table.lower(), engine, if_exists='replace', index=False, chunksize=1000)
        log.append('MDB 数据导入成功')
    except Exception as e:
        log.append(f'MDB 导入失败: {e}')

    print('正在导入 XLS 代码表...')
    try:
        if os.path.exists(xls_path):
            df_xls = pd.read_excel(xls_path)
            df_xls.rename(columns={'权属单位代码': 'qsdwdm', '权属单位名称': 'qsdwmc'}, inplace=True)
            df_xls.to_sql('qsdwdmb', engine, if_exists='replace', index=False)
            log.append('XLS 代码表导入成功')
        else:
            log.append('未发现 XLS 代码表，跳过')
    except Exception as e:
        log.append(f'XLS 导入失败: {e}')
        
    return log

def import_data():
    default_dir = r'G:\全椒县二轮延包\全椒县县级验收管理平台\sources\341124100'
    import_data_from_path(default_dir)

if __name__ == '__main__':
    print('注意：请先确保 PostgreSQL 在 localhost:5432 运行，并创建了 quanjiao 数据库。')
    import_data()
