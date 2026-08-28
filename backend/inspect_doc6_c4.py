import win32com.client, os, pythoncom
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
doc_path = os.path.join(base_dir, "附件", "附件6.doc")
doc = word.Documents.Open(doc_path)

with open(os.path.join(base_dir, "backend", "doc6_c4_details.txt"), "w", encoding="utf-8") as out:
    for idx in range(1, doc.Tables.Count + 1):
        t = doc.Tables(idx)
        out.write(f"\n================ TABLE {idx} ================\n")
        for r in range(1, t.Rows.Count + 1):
            if t.Rows(r).Cells.Count >= 4:
                item_name = t.Rows(r).Cells(2).Range.Text.strip().replace("\r", "").replace("\x07", "")
                c4 = t.Rows(r).Cells(4).Range.Text.strip().replace("\r", "").replace("\x07", "")
                out.write(f"R{r} [{item_name}]:\n  {repr(c4)}\n")
            else:
                out.write(f"R{r}: {[t.Rows(r).Cells(c).Range.Text.strip().replace(chr(13),'').replace(chr(7),'') for c in range(1, t.Rows(r).Cells.Count+1)]}\n")

doc.Close(False)
word.Quit()
pythoncom.CoUninitialize()
print("Done")