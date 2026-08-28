import win32com.client, os, pythoncom, shutil

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件6.doc")
out_path = os.path.join(base_dir, "backend", "downloads", "test_spacing.doc")
shutil.copy(tpl, out_path)

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)

p = doc.Paragraphs(3)
rng = p.Range
rng.End = rng.End - 1
rng.Text = "行政区划名称：全椒县襄河镇                     验收内容：机制运行                            2026 年       月      日"

print("Lines count of paragraph 3:", len(p.Range.Text.split("\r")))
print("P3 text:", repr(p.Range.Text.replace("\r", "")))

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()