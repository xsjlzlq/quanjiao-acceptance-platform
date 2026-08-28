import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件8.doc")
doc = word.Documents.Open(tpl)
t = doc.Tables(1)
r8 = t.Rows(8)
for c in range(1, r8.Cells.Count + 1):
    cell = r8.Cells(c)
    print(f"R8 Cell {c} width: {cell.Width}")

r1 = t.Rows(1)
for c in range(1, r1.Cells.Count + 1):
    print(f"R1 Cell {c} width: {r1.Cells(c).Width}")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()