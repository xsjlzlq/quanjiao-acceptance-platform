import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件6.doc")
doc = word.Documents.Open(tpl)

t = doc.Tables(1)
pre_range = doc.Range(0, t.Range.Start)
count = pre_range.Paragraphs.Count
print(f"Total paragraphs before table 1: {count}")
for i in range(1, count + 1):
    print(f"  P{i}: {repr(pre_range.Paragraphs(i).Range.Text)}")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()