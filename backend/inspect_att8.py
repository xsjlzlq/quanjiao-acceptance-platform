import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件8.doc")
doc = word.Documents.Open(tpl)

print("Paragraphs:", doc.Paragraphs.Count)
for i in range(1, min(10, doc.Paragraphs.Count + 1)):
    t = doc.Paragraphs(i).Range.Text.strip().replace("\r", "").replace("\x07", "")
    if t:
        print(f"P{i}: {t}")

print("\nTables:", doc.Tables.Count)
t = doc.Tables(1)
print("Table 1 rows:", t.Rows.Count, "cols:", t.Columns.Count)
for r in range(1, min(10, t.Rows.Count + 1)):
    cells = t.Rows(r).Cells
    row_vals = [cells(c).Range.Text.strip().replace("\r", "").replace("\x07", "") for c in range(1, cells.Count + 1)]
    print(f"Row {r} (cells={cells.Count}): {row_vals}")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()