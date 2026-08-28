import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件8.doc")
doc = word.Documents.Open(tpl)
t = doc.Tables(1)
r8 = t.Rows(8)
print("Row 8 cells count:", r8.Cells.Count)
for c in range(1, r8.Cells.Count + 1):
    print(f"  R8 C{c}: {repr(r8.Cells(c).Range.Text.strip().replace(chr(13),'').replace(chr(7),''))}")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()