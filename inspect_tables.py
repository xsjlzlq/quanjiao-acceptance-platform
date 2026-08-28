import win32com.client, os, pythoncom
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

doc = word.Documents.Open(os.path.abspath(r"../附件/附件6.doc"))
for idx in range(1, 5):
    t = doc.Tables(idx)
    print(f"=== Table {idx} ===")
    for r in range(1, t.Rows.Count + 1):
        cells = t.Rows(r).Cells
        cell_info = []
        for c in range(1, cells.Count + 1):
            txt = cells(c).Range.Text.strip().replace("\r", "").replace("\x07", "")
            cell_info.append(f"C{c}:{repr(txt)}")
        print(f"Row {r} (count={cells.Count}): " + ", ".join(cell_info))

doc.Close(False)
word.Quit()
pythoncom.CoUninitialize()