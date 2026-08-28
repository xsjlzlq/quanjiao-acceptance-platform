import os
from doc_exporter import export_att5, export_waiye_att8

stats = [{
    "序号": 1, "乡镇名称": "襄河镇", "村名称": "邱塔村", "组名称": "第一组",
    "发包方总户数": 40, "抽样农户数5%": 2
}]

u5 = export_att5(stats, "341124100", "襄河镇")
print("Att5 url:", u5)

rows = [
    {
        "cbfmc": "张三", "cbfbm_short": "0123", "lxdh": "13800000001",
        "dkmc": "门前田", "dkbm_short": "00101", "scmj": 2.35,
        "area_acknowledged": "X", "rights_correct": "", "bound_correct": "",
        "member_qualified": "", "self_verified": "", "self_signed": "",
        "satisfaction": "满意", "survey_method": "现场"
    }
]
u8 = export_waiye_att8("襄河镇", "邱塔村", "第一组", rows)
print("Att8 url:", u8)