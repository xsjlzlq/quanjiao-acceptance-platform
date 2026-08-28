import win32com.client, os, pythoncom, shutil
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件6.doc")
out_path = os.path.join(base_dir, "backend", "downloads", "test_att6_county.doc")
os.makedirs(os.path.dirname(out_path), exist_ok=True)
shutil.copy(tpl, out_path)

doc = word.Documents.Open(out_path)
print("Initial tables:", doc.Tables.Count)

# If we want only Table 1 (1/4):
# Range from P67 start to end of doc
p67 = doc.Paragraphs(67)
rng = doc.Range(p67.Range.Start, doc.Content.End)
rng.Delete()

print("After delete, tables:", doc.Tables.Count)
print("Paragraphs:", doc.Paragraphs.Count)
doc.Save()
doc.Close(False)
word.Quit()
pythoncom.CoUninitialize()
print("Test county 1/4 success!")