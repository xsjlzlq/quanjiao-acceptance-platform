import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

doc_path = r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\downloads\附件6_全椒县县级自查内业组检查记录表_襄河镇.doc"
doc = word.Documents.Open(doc_path)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\dump_xianghe_lines.txt", "w", encoding="utf-8") as out:
    for t_idx in range(1, doc.Tables.Count + 1):
        t = doc.Tables(t_idx)
        out.write(f"\n================ TABLE {t_idx} ================\n")
        for r in range(2, t.Rows.Count - 1):
            if t.Rows(r).Cells.Count >= 4:
                item_title = t.Rows(r).Cells(2).Range.Text.strip().replace("\r", "").replace("\x07", "")
                raw_c4 = t.Rows(r).Cells(4).Range.Text.replace("\x07", "")
                out.write(f"--- R{r} [{item_title}] ---\n")
                for line in raw_c4.split("\r"):
                    if line:
                        out.write(f"  {line}\n")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()
print("dump_xianghe_lines.txt written.")