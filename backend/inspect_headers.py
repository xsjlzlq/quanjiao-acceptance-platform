import win32com.client, os, pythoncom
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
doc_path = os.path.join(base_dir, "附件", "附件6.doc")
doc = word.Documents.Open(doc_path)

for idx in range(1, 5):
    t = doc.Tables(idx)
    # find paragraph right before table
    rng = t.Range
    start_pos = rng.Start
    print(f"Table {idx} start: {start_pos}")
    # find paragraphs near start_pos
    for p_idx in range(1, doc.Paragraphs.Count + 1):
        p = doc.Paragraphs(p_idx)
        if abs(p.Range.Start - start_pos) < 300:
            print(f"  P{p_idx} (pos {p.Range.Start}): {repr(p.Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}")

doc.Close(False)
word.Quit()
pythoncom.CoUninitialize()