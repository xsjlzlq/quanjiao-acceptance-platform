import win32com.client, os, pythoncom

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0

doc_path = r"G:\全椒县二轮延包\全椒县县级验收管理平台\附件\附件9.doc"
doc = word.Documents.Open(doc_path)
full_text = doc.Content.Text
with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\att9_content.txt", "w", encoding="utf-8") as out:
    out.write(full_text)

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()
print("Read content text OK!")