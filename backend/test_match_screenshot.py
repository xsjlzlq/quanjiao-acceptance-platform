import requests, win32com.client, pythoncom, os

# 1. Save County (mech = 12.5) -> full 15 - 2.5 deduct (e.g. mech_3 没有宣传扣2 + mech_4 一项扣0.5 = 2.5 deduct)
r = requests.post('http://127.0.0.1:8081/api/save_neiye', json={
    'qsdwdm': '341124', 'qsdwmc': '全椒县 (县级)', 'level': 'county',
    'form_data': {'mech_3': ['没有宣传材料'], 'mech_4': ['没有培训材料']},
    'score': 12.5
})
print("Save county:", r.json())

# 2. Save Xianghe (mech = 9, prog = 29, policy = 12, effect = 9, total = 59)
r = requests.post('http://127.0.0.1:8081/api/save_neiye', json={
    'qsdwdm': '341124100', 'qsdwmc': '襄河镇', 'level': 'township',
    'form_data': {
        'mech_1': ['未制定方案'], 'mech_2': ['支付不规范'], # mech deduct = 6 -> score = 9
        'prog_4': ['各类资料制作粗糙', '各类资料签署不规范'], # prog deduct = 1 -> score = 29
        'policy_1': ['打乱重分', '小调整比率过大或手续不齐全', '违法调整或收回承包地'], # policy deduct = 3 -> score = 12
        'effect_1': ['未建立矛盾纠纷处置机制'] # effect deduct = 1 -> score = 9
    },
    'score': 59.0
})
print("Save Xianghe:", r.json())

# 3. Save Dashu (mech = 14.5, prog = 29.5, policy = 14, effect = 10, total = 68)
r = requests.post('http://127.0.0.1:8081/api/save_neiye', json={
    'qsdwdm': '341124102', 'qsdwmc': '大墅镇', 'level': 'township',
    'form_data': {
        'mech_4': ['没有培训材料'], # mech deduct = 0.5 -> score = 14.5
        'prog_2': ['户变化未统计'], # prog deduct = 0.5 -> score = 29.5
        'policy_1': ['打乱重分'], # policy deduct = 1 -> score = 14
        'effect_1': [] # effect deduct = 0 -> score = 10
    },
    'score': 68.0
})
print("Save Dashu:", r.json())

# 4. Trigger Export Att7
r_att7 = requests.get('http://127.0.0.1:8081/api/export_neiye_att7')
print("Export Att7 response:", r_att7.json())

# 5. Inspect generated Att7
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
f_att7 = os.path.join(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\downloads", "附件7_全椒县县级自查内业组检查得分表.doc")
d7 = word.Documents.Open(f_att7)
t = d7.Tables(1)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\screenshot_match_verify.txt", "w", encoding="utf-8") as out:
    for r in range(1, 14):
        vals = [t.Rows(r).Cells(c).Range.Text.strip().replace(chr(13),'').replace(chr(7),'') for c in range(1, 8)]
        out.write(f"Row {r:2d}: {vals}\n")

d7.Close(0)
word.Quit()
pythoncom.CoUninitialize()