import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件6.doc")
doc = word.Documents.Open(tpl)

for i in range(1, doc.Paragraphs.Count + 1):
    txt = doc.Paragraphs(i).Range.Text.strip().replace("\r", "").replace("\x07", "")
    if "行政区划名称" in txt:
        print(f"P{i}: raw={repr(doc.Paragraphs(i).Range.Text)}")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()