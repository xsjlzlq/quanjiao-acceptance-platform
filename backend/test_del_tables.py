import win32com.client, os, pythoncom, shutil

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件6.doc")
out_path = os.path.join(base_dir, "backend", "downloads", "test_delete_tables.doc")
shutil.copy(tpl, out_path)

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
doc = word.Documents.Open(out_path)

print("Tables before:", doc.Tables.Count)

# Delete Table 4, 3, 2 in reverse order
while doc.Tables.Count > 1:
    doc.Tables(doc.Tables.Count).Delete()

print("Tables after deleting tables:", doc.Tables.Count)

# Delete paragraphs after table 1
t1_end = doc.Tables(1).Range.End
# Find paragraph of table 1 end
# Keep paragraph 66 (检查者：... 复核者：) which is right after table 1
# Let's find the paragraph containing "复核者：" after Table 1
end_pos = doc.Content.End
for p in doc.Paragraphs:
    if "复核者：" in p.Range.Text:
        end_pos = p.Range.End
        break

if end_pos < doc.Content.End:
    rng = doc.Range(end_pos, doc.Content.End)
    rng.Delete()

print("Tables final:", doc.Tables.Count)
print("Paragraphs final:", doc.Paragraphs.Count)

doc.Save()
doc.Close(False)
word.Quit()
pythoncom.CoUninitialize()
print("Success deleting tables!")