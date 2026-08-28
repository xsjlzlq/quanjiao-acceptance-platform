import win32com.client, os, pythoncom
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件6.doc")
doc = word.Documents.Open(tpl)
t1 = doc.Tables(1)
c4 = t1.Rows(2).Cells(4).Range.Text
print("Raw c4:", repr(c4))
for ch in c4[:10]:
    print(f"char: {repr(ch)}, ord: {ord(ch)}, hex: {hex(ord(ch))}")
doc.Close(False)
word.Quit()
pythoncom.CoUninitialize()