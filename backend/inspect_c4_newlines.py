import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件6.doc")
doc = word.Documents.Open(tpl)

for idx in range(1, 5):
    t = doc.Tables(idx)
    print(f"=== Table {idx} ===")
    for r in range(2, t.Rows.Count - 1):
        if t.Rows(r).Cells.Count >= 4:
            c4 = t.Rows(r).Cells(4).Range.Text
            print(f"R{r} raw: {repr(c4)}")

doc.Close(False)
word.Quit()
pythoncom.CoUninitialize()