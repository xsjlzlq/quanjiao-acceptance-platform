import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

doc_path = r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\downloads\test_att8_filled_custom.doc"
doc = word.Documents.Open(doc_path)
t = doc.Tables(1)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\att8_filled_dump.txt", "w", encoding="utf-8") as out:
    out.write(f"Header: {repr(doc.Paragraphs(3).Range.Text)}\n")
    out.write(f"Rows count: {t.Rows.Count}\n")
    for r in range(1, t.Rows.Count + 1):
        vals = [t.Rows(r).Cells(c).Range.Text.strip().replace("\r","").replace("\x07","") for c in range(1, t.Rows(r).Cells.Count + 1)]
        out.write(f"Row {r}: {vals}\n")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()
print("Dumped.")