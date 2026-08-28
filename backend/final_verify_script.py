import requests, time, os, win32com.client, pythoncom

# 1. County Att6
r1 = requests.post('http://127.0.0.1:8081/api/export_neiye_att6', json={
    'qsdwdm': '341124', 'qsdwmc': '全椒县', 'level': 'county',
    'form_data': {'mech_1': ['未制定方案']}
})
print('1. County Att6:', r1.json())

# 2. Township Att6
r2 = requests.post('http://127.0.0.1:8081/api/export_neiye_att6', json={
    'qsdwdm': '341124100', 'qsdwmc': '襄河镇', 'level': 'township',
    'form_data': {'mech_1': ['直接套用上级方案'], 'policy_2_1': 1, 'prog_2': ['没有进行摸底', '承包地变化未摸清']}
})
print('2. Township Att6:', r2.json())

# 3. Att7
r3 = requests.get('http://127.0.0.1:8081/api/export_neiye_att7')
print('3. Att7:', r3.json())

# Inspect the resulting files
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

downloads_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\downloads"

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\final_verify.txt", "w", encoding="utf-8") as out:
    # 1. County Att6 header
    f1 = os.path.join(downloads_dir, "附件6_全椒县县级自查内业组检查记录表_1_4.doc")
    d1 = word.Documents.Open(f1)
    t1 = d1.Tables(1)
    p = d1.Range(0, t1.Range.Start).Paragraphs(d1.Range(0, t1.Range.Start).Paragraphs.Count)
    out.write(f"County Header: {repr(p.Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}\n")
    d1.Close(0)

    # 2. Township Att6 headers
    f2 = os.path.join(downloads_dir, "附件6_全椒县县级自查内业组检查记录表_襄河镇.doc")
    d2 = word.Documents.Open(f2)
    for idx in range(1, 5):
        t = d2.Tables(idx)
        p = d2.Range(0, t.Range.Start).Paragraphs(d2.Range(0, t.Range.Start).Paragraphs.Count)
        out.write(f"Township Table {idx} Header: {repr(p.Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}\n")
    d2.Close(0)

    # 3. Att7 table rows
    f3 = os.path.join(downloads_dir, "附件7_全椒县县级自查内业组检查得分表.doc")
    d3 = word.Documents.Open(f3)
    t3 = d3.Tables(1)
    out.write("\n=== Att7 Table ===\n")
    for r in range(1, 14):
        vals = [t3.Rows(r).Cells(c).Range.Text.strip().replace(chr(13),'').replace(chr(7),'') for c in range(1, 8)]
        out.write(f"R{r}: {vals}\n")
    d3.Close(0)

word.Quit()
pythoncom.CoUninitialize()
print("Final verify file written.")