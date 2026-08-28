import win32com.client, os, pythoncom
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
out_path = os.path.join(base_dir, "backend", "downloads", "test_att6_filled.doc")
doc = word.Documents.Open(out_path)

print("P3 text:", repr(doc.Paragraphs(3).Range.Text.strip().replace(chr(13),'').replace(chr(7),'')))
t1 = doc.Tables(1)
print("R2 C4:", repr(t1.Rows(2).Cells(4).Range.Text.strip().replace(chr(13),'').replace(chr(7),'')))
print("R2 C6:", repr(t1.Rows(2).Cells(6).Range.Text.strip().replace(chr(13),'').replace(chr(7),'')))
print("R6 C3 (总计扣分):", repr(t1.Rows(6).Cells(3).Range.Text.strip().replace(chr(13),'').replace(chr(7),'')))
print("R7 C2 (重要问题描述):", repr(t1.Rows(7).Cells(2).Range.Text.strip().replace(chr(13),'').replace(chr(7),'')))

doc.Close(False)
word.Quit()
pythoncom.CoUninitialize()