import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件8.doc")
doc = word.Documents.Open(tpl)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\att8_structure.txt", "w", encoding="utf-8") as out:
    t = doc.Tables(1)
    out.write(f"Header P3: {repr(doc.Paragraphs(3).Range.Text)}\n")
    out.write(f"Rows count: {t.Rows.Count}\n")
    for r in range(1, t.Rows.Count + 1):
        cells = t.Rows(r).Cells
        vals = [cells(c).Range.Text.strip().replace("\r", "").replace("\x07", "") for c in range(1, cells.Count + 1)]
        out.write(f"Row {r} (cells={cells.Count}): {vals}\n")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()
print("att8_structure.txt written.")