import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

downloads_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\downloads"

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\verify_result.txt", "w", encoding="utf-8") as out:
    # 1. Inspect County Att6 (1/4)
    f1 = os.path.join(downloads_dir, "附件6_全椒县县级自查内业组检查记录表（1_4）.doc")
    doc1 = word.Documents.Open(f1)
    out.write("=== County Att6 (1/4) ===\n")
    out.write(f"Tables count: {doc1.Tables.Count}\n")
    t1 = doc1.Tables(1)
    out.write(f"R2 C4: {repr(t1.Rows(2).Cells(4).Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}\n")
    out.write(f"R3 C4: {repr(t1.Rows(3).Cells(4).Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}\n")
    out.write(f"R6 C3 (总计扣分): {repr(t1.Rows(6).Cells(3).Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}\n")
    out.write(f"R7 C2 (重要问题描述): {repr(t1.Rows(7).Cells(2).Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}\n")
    doc1.Close(False)

    # 2. Inspect Xianghe Att6 (all 4 parts)
    f2 = os.path.join(downloads_dir, "附件6_全椒县县级自查内业组检查记录表_襄河镇.doc")
    doc2 = word.Documents.Open(f2)
    out.write("\n=== Xianghe Att6 (4/4) ===\n")
    out.write(f"Tables count: {doc2.Tables.Count}\n")
    t3 = doc2.Tables(3)
    out.write(f"T3 R3 C4 (保障权益): {repr(t3.Rows(3).Cells(4).Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}\n")
    out.write(f"T3 R4 C4 (消亡户): {repr(t3.Rows(4).Cells(4).Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}\n")
    doc2.Close(False)

    # 3. Inspect Att7
    f3 = os.path.join(downloads_dir, "附件7_全椒县县级自查内业组检查得分表.doc")
    doc3 = word.Documents.Open(f3)
    out.write("\n=== Att7 得分表 ===\n")
    t_att7 = doc3.Tables(1)
    for r in range(1, t_att7.Rows.Count + 1):
        vals = [t_att7.Rows(r).Cells(c).Range.Text.strip().replace(chr(13),'').replace(chr(7),'') for c in range(1, t_att7.Rows(r).Cells.Count + 1)]
        out.write(f"Row {r}: {vals}\n")
    doc3.Close(False)

word.Quit()
pythoncom.CoUninitialize()
print("Verification file written.")