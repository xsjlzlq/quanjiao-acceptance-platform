import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件9.doc")
doc = word.Documents.Open(tpl)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\att9_structure.txt", "w", encoding="utf-8") as out:
    t = doc.Tables(1)
    out.write(f"Title P2: {repr(doc.Paragraphs(2).Range.Text)}\n")
    out.write(f"Rows count: {t.Rows.Count}\n")
    out.write(f"Columns count: {t.Columns.Count}\n")
    
    # Iterate through all cells in table
    for r in range(1, t.Rows.Count + 1):
        row_vals = []
        for c in range(1, t.Columns.Count + 1):
            try:
                cell = t.Cell(r, c)
                txt = cell.Range.Text.strip().replace("\r", "").replace("\x07", "")
                row_vals.append(f"C{c}:{txt}")
            except Exception as e:
                row_vals.append(f"C{c}:<merged>")
        out.write(f"Row {r}: " + " | ".join(row_vals) + "\n")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()
print("att9_structure.txt written.")