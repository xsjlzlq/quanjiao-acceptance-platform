import win32com.client, os, pythoncom
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件6.doc")
doc = word.Documents.Open(tpl)
p3 = doc.Paragraphs(3).Range.Text
print("P3 raw:", repr(p3))
print("P3 codes:", [ord(c) for c in p3])
doc.Close(False)
word.Quit()
pythoncom.CoUninitialize()