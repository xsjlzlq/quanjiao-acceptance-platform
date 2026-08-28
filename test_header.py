import os
import win32com.client

word = win32com.client.DispatchEx('Word.Application')
doc = word.Documents.Open(os.path.abspath(r'附件\附件8.doc'), ReadOnly=True)
for i in range(1, min(5, doc.Paragraphs.Count + 1)):
    print(f"P{i}: {repr(doc.Paragraphs(i).Range.Text)}")
doc.Close(False)
word.Quit()
