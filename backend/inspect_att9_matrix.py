import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0

doc_path = r"G:\全椒县二轮延包\全椒县县级验收管理平台\附件\附件9.doc"
doc = word.Documents.Open(doc_path)
t = doc.Tables(1)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\att9_cells_matrix.txt", "w", encoding="utf-8") as out:
    for r in range(1, 13):
        row_str = []
        for c in range(1, 10):
            try:
                cell = t.Cell(r, c)
                txt = cell.Range.Text.strip().replace("\r", " ").replace("\x07", "")
                row_str.append(f"C{c}:{txt}")
            except Exception as e:
                pass
        out.write(f"R{r}: " + " | ".join(row_str) + "\n")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()
print("Done matrix.")