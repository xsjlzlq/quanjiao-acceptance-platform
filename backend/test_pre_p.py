import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件6.doc")
doc = word.Documents.Open(tpl)

for idx in range(1, doc.Tables.Count + 1):
    t = doc.Tables(idx)
    # The paragraph right before the table:
    pre_range = doc.Range(0, t.Range.Start)
    last_p = pre_range.Paragraphs(pre_range.Paragraphs.Count)
    print(f"Table {idx} preceding paragraph: {repr(last_p.Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()