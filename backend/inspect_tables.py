import win32com.client, os, pythoncom
pythoncom.CoInitialize()
try:
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False

    doc_path = r"G:\全椒县二轮延包\全椒县县级验收管理平台\附件\附件6.doc"
    doc = word.Documents.Open(doc_path)
    with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\tables_info.txt", "w", encoding="utf-8") as out:
        for idx in range(1, doc.Tables.Count + 1):
            t = doc.Tables(idx)
            out.write(f"=== Table {idx} ===\n")
            for r in range(1, t.Rows.Count + 1):
                cells = t.Rows(r).Cells
                cell_info = []
                for c in range(1, cells.Count + 1):
                    txt = cells(c).Range.Text.strip().replace("\r", "").replace("\x07", "")
                    cell_info.append(f"C{c}:{repr(txt)}")
                out.write(f"Row {r} (count={cells.Count}): " + ", ".join(cell_info) + "\n")

    doc.Close(False)
    word.Quit()
    print("DONE")
except Exception as e:
    print("ERROR:", e)
finally:
    pythoncom.CoUninitialize()