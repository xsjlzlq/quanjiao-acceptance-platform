import win32com.client, os, pythoncom
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
doc_path = os.path.join(base_dir, "附件", "附件6.doc")
doc = word.Documents.Open(doc_path)

for idx in range(1, 5):
    t = doc.Tables(idx)
    print(f"=== Table {idx} ===")
    total_r = t.Rows.Count - 1
    desc_r = t.Rows.Count
    print(f"Total row ({total_r}): {t.Rows(total_r).Cells.Count} cells")
    for c in range(1, t.Rows(total_r).Cells.Count + 1):
        print(f"  C{c}: {repr(t.Rows(total_r).Cells(c).Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}")
    print(f"Desc row ({desc_r}): {t.Rows(desc_r).Cells.Count} cells")
    for c in range(1, t.Rows(desc_r).Cells.Count + 1):
        print(f"  C{c}: {repr(t.Rows(desc_r).Cells(c).Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}")

doc.Close(False)
word.Quit()
pythoncom.CoUninitialize()