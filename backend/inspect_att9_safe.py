import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件9.doc")
doc = word.Documents.Open(FileName=tpl, ReadOnly=False, ConfirmConversions=False)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\att9_structure.txt", "w", encoding="utf-8") as out:
    out.write(f"Title P2: {repr(doc.Paragraphs(2).Range.Text)}\n")
    t = doc.Tables(1)
    
    # We can inspect cells safely
    out.write(f"Table cells count: {t.Range.Cells.Count}\n")
    for idx in range(1, t.Range.Cells.Count + 1):
        c = t.Range.Cells(idx)
        txt = c.Range.Text.strip().replace("\r","").replace("\x07","")
        out.write(f"Cell {idx} (R{c.RowIndex}, C{c.ColumnIndex}): {repr(txt)}\n")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()
print("Done inspecting 附件9.doc")