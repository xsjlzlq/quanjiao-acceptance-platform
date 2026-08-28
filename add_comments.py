# -*- coding: utf-8 -*-
import psycopg2

comments = {
    'dkxx_shp_attrs': {
        'ysdm': '要素代码', 'dkbm': '地块编码', 'dkmc': '地块名称', 'syqxz': '所有权性质', 
        'dklb': '地块类别', 'tdlylx': '土地利用类型', 'tdyt': '土地用途', 'sfjbnt': '是否基本农田', 
        'scmj': '实测面积', 'dkdz': '地块东至', 'dkxz': '地块西至', 'dknz': '地块南至', 
        'dkbz': '地块北至', 'dkbzxx': '地块备注信息', 'zjrxm': '指界人姓名', 'dldj': '地力等级', 
        'bsm': '标识码', 'kjzb': '空间坐标', 'scmjm': '实测面积亩'
    },
    'cbdkxx': {
        'dkbm': '地块编码', 'fbfbm': '发包方编码', 'cbfbm': '承包方编码', 'cbjyqqdfs': '承包经营权取得方式',
        'htmj': '合同面积', 'cbhtbm': '承包合同编码', 'lzhtbm': '流转合同编码', 'cbjyqzbm': '承包经营权证编码',
        'yhtmj': '原合同面积', 'htmjm': '合同面积亩', 'yhtmjm': '原合同面积亩', 'sfqqqg': '是否确权确股'
    },
    'cbf': {
        'cbfbm': '承包方编码', 'cbflx': '承包方类型', 'cbfmc': '承包方名称', 'cbfzjlx': '承包方证件类型',
        'cbfzjhm': '承包方证件号码', 'cbfdz': '承包方地址', 'yzbm': '邮政编码', 'lxdh': '联系电话',
        'cbfcysl': '承包方成员数量', 'cbfdcrq': '调查日期', 'cbfdcy': '调查员', 'cbfdcjs': '调查记事',
        'gsjs': '公示记事', 'gsjsr': '公示记事人', 'gsshrq': '审核日期', 'gsshr': '审核人'
    },
    'cbf_jtcy': {
        'cbfbm': '承包方编码', 'cyxm': '成员姓名', 'cyxb': '成员性别', 'cyzjlx': '成员证件类型',
        'cyzjhm': '成员证件号码', 'yhzgx': '与户主关系', 'cybz': '成员备注', 'sfgyr': '是否共有人',
        'cybzsm': '成员备注说明'
    },
    'fbf': {
        'fbfbm': '发包方编码', 'fbfmc': '发包方名称', 'fbfzjlx': '发包方证件类型', 'fbfzjhm': '发包方证件号码',
        'fbfdz': '发包方地址', 'fzrxm': '负责人姓名', 'lxdh': '联系电话', 'dzyj': '电子邮件'
    },
    'cbht': {
        'cbhtbm': '承包合同编码', 'ycbhtbm': '原承包合同编码', 'fbfbm': '发包方编码', 'cbfbm': '承包方编码',
        'cbqssj': '承包起始时间', 'cbjssj': '承包结束时间', 'htzmj': '合同总面积', 'cbdkzs': '承包地块总数',
        'qdrq': '签订日期'
    },
    'cbjyqz': {
        'cbjyqzbm': '承包经营权证编码', 'yqzbm': '原权证编码', 'fzjg': '发证机关', 'fzrq': '发证日期',
        'qzsflq': '权证是否领取', 'qzlqrxm': '权证领取人姓名', 'qzlqrq': '权证领取日期'
    }
}

try:
    con = psycopg2.connect(dbname='quanjiao', user='postgres', password='123456', host='localhost', port='5432')
    con.autocommit = True
    cursor = con.cursor()
    for table, cols in comments.items():
        cursor.execute("SELECT 1 FROM information_schema.tables WHERE table_name=%s", (table,))
        if cursor.fetchone():
            for col, comment in cols.items():
                try:
                    cursor.execute(f"COMMENT ON COLUMN {table}.{col} IS '{comment}';")
                except Exception as e:
                    pass
    print('Comments added successfully.')
    cursor.close()
    con.close()
except Exception as e:
    print('Error:', e)
