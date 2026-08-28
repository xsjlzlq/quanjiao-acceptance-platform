import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0

doc_path = r"G:\全椒县二轮延包\全椒县县级验收管理平台\附件\附件9.doc"
doc = word.Documents.Open(doc_path)
t = doc.Tables(1)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\att9_rows_detail.txt", "w", encoding="utf-8") as out:
    out.write(f"Rows count: {t.Rows.Count}\n")
    for r in range(1, t.Rows.Count + 1):
        cell_texts = []
        # Word table rows can be accessed via Cells
        try:
            for c in range(1, t.Rows(r).Cells.Count + 1):
                txt = t.Rows(r).Cells(c).Range.Text.strip().replace("\r", " ").replace("\x07", "")
                cell_texts.append(f"C{c}:{txt}")
            out.write(f"R{r} (cells={t.Rows(r).Cells.Count}): " + " | ".join(cell_texts) + "\n")
        except Exception as e:
            out.write(f"R{r} error: {e}\n")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()
print("Done.")