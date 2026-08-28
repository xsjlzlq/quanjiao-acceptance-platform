import win32com.client, os, pythoncom
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
doc_path = os.path.join(base_dir, "附件", "附件7.doc")
doc = word.Documents.Open(doc_path)
t = doc.Tables(1)
with open(os.path.join(base_dir, "backend", "att7_info.txt"), "w", encoding="utf-8") as out:
    for r in range(1, t.Rows.Count + 1):
        cells = t.Rows(r).Cells
        row_text = [cells(c).Range.Text.strip().replace("\r", "").replace("\x07", "") for c in range(1, cells.Count + 1)]
        out.write(f"Row {r}: {row_text}\n")
doc.Close(False)
word.Quit()
pythoncom.CoUninitialize()
print("Done")