import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

f_town = r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\downloads\附件6_全椒县县级自查内业组检查记录表_襄河镇.doc"
doc_t = word.Documents.Open(f_town)

for idx in range(1, doc_t.Tables.Count + 1):
    t = doc_t.Tables(idx)
    pre_range = doc_t.Range(0, t.Range.Start)
    header_p = pre_range.Paragraphs(pre_range.Paragraphs.Count)
    txt = header_p.Range.Text.strip().replace(chr(13),'').replace(chr(7),'')
    print(f"Table {idx} Header: {repr(txt)}")

doc_t.Close(0)
word.Quit()
pythoncom.CoUninitialize()