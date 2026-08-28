import time, os, win32com.client, pythoncom
from doc_exporter import export_neiye_att6_county, export_neiye_att6_township, export_neiye_att7

sample_form_town = {
    "mech_1": ["直接套用上级方案", "未制定方案"],
    "mech_2": ["支付不及时"],
    "prog_1": ["未召开会议"],
    "prog_2": ["没有进行摸底"],
    "policy_1": ["打乱重分"],
    "policy_2_1": 2,
    "effect_1": ["未建立矛盾纠纷处置机制"]
}

sample_form_dashu = {
    "mech_4": ["没有培训材料"],
    "prog_4": ["各类资料制作粗糙"],
    "policy_1": ["打乱重分"]
}

u1 = export_neiye_att6_county({"mech_1": ["未制定方案"]})
print("County export URL:", u1)

u2 = export_neiye_att6_township("襄河镇", sample_form_town)
print("Township export URL:", u2)

u3 = export_neiye_att7({
    "341124": {"form_data": {"mech_1": ["未制定方案"]}},
    "341124100": {"form_data": sample_form_town},
    "341124102": {"form_data": sample_form_dashu}
})
print("Att7 export URL:", u3)

# Verify generated contents
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

downloads_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\downloads"

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\verify_fix_result.txt", "w", encoding="utf-8") as out:
    # 1. Check Township Att6 headers
    f_town = os.path.join(downloads_dir, "附件6_全椒县县级自查内业组检查记录表_襄河镇.doc")
    doc_t = word.Documents.Open(f_town)
    out.write("=== 附件6 襄河镇 Headers ===\n")
    for idx in [3, 68, 188, 253]:
        if idx <= doc_t.Paragraphs.Count:
            out.write(f"P{idx}: {repr(doc_t.Paragraphs(idx).Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}\n")
    doc_t.Close(0)

    # 2. Check County Att6 header
    f_county = os.path.join(downloads_dir, "附件6_全椒县县级自查内业组检查记录表_1_4.doc")
    doc_c = word.Documents.Open(f_county)
    out.write("\n=== 附件6 全椒县 (1/4) Header ===\n")
    out.write(f"P3: {repr(doc_c.Paragraphs(3).Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}\n")
    doc_c.Close(0)

    # 3. Check Att7 Table
    f_att7 = os.path.join(downloads_dir, "附件7_全椒县县级自查内业组检查得分表.doc")
    doc_7 = word.Documents.Open(f_att7)
    out.write("\n=== 附件7 Table ===\n")
    t7 = doc_7.Tables(1)
    for r in range(1, 14):
        vals = [t7.Rows(r).Cells(c).Range.Text.strip().replace(chr(13),'').replace(chr(7),'') for c in range(1, 8)]
        out.write(f"R{r}: {vals}\n")
    doc_7.Close(0)

word.Quit()
pythoncom.CoUninitialize()
print("Verification finished.")