import os
import win32com.client

word = win32com.client.DispatchEx('Word.Application')
doc = word.Documents.Open(os.path.abspath(r'附件\附件8.doc'), ReadOnly=True)
for i in range(1, 6):
    try:
        print(f"P{i}: {repr(doc.Paragraphs(i).Range.Text)}")
    except Exception as e:
        print(f"P{i}: error {e}")
doc.Close(False)
word.Quit()
