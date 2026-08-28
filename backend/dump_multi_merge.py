import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0

doc_path = r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\downloads\test_multi_merge.doc"
doc = word.Documents.Open(doc_path)
t = doc.Tables(1)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\multi_merge_dump.txt", "w", encoding="utf-8") as out:
    out.write(f"Rows count: {t.Rows.Count}\n")
    # check shapes count
    out.write(f"InlineShapes count: {doc.InlineShapes.Count}\n")
    for idx in range(1, doc.InlineShapes.Count + 1):
        s = doc.InlineShapes(idx)
        out.write(f"  Shape {idx}: width={s.Width}, height={s.Height}\n")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()
print("Dumped.")