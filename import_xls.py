# -*- coding: utf-8 -*-
import pandas as pd
from sqlalchemy import create_engine
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DATABASE_URL_SYNC = "postgresql://postgres:123456@localhost:5432/quanjiao"
engine = create_engine(DATABASE_URL_SYNC)

xls_path = r'G:\全椒县二轮延包\全椒县县级验收管理平台\sources\341124100\权属数据\3411242026权属单位代码表.xls'

print('正在导入 XLS 权属单位代码表...')
try:
    df_xls = pd.read_excel(xls_path)
    # 标准化列名：转换为小写拼音缩写或保持原始名称的拼音首字母
    # 原始列：权属单位代码，权属单位名称
    df_xls.rename(columns={'权属单位代码': 'qsdwdm', '权属单位名称': 'qsdwmc'}, inplace=True)
    df_xls.to_sql('qsdwdmb', engine, if_exists='replace', index=False)
    
    # 增加中文注释
    import psycopg2
    con = psycopg2.connect(dbname='quanjiao', user='postgres', password='123456', host='localhost', port='5432')
    con.autocommit = True
    cursor = con.cursor()
    cursor.execute("COMMENT ON TABLE qsdwdmb IS '权属单位代码表';")
    cursor.execute("COMMENT ON COLUMN qsdwdmb.qsdwdm IS '权属单位代码';")
    cursor.execute("COMMENT ON COLUMN qsdwdmb.qsdwmc IS '权属单位名称';")
    cursor.close()
    con.close()
    
    print('XLS 权属单位代码表导入成功，并已追加中文注释。')
except Exception as e:
    print('XLS 导入失败:', e)
