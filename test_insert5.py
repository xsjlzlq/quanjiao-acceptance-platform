import os
import win32com.client

word = win32com.client.DispatchEx('Word.Application')
word.Visible = False
doc = word.Documents.Open(os.path.abspath(r'附件\附件5.doc'))
t5 = doc.Tables(1)
print("Rows before:", t5.Rows.Count)
while t5.Rows.Count > 2:
    t5.Rows(3).Delete()
print("Rows after delete:", t5.Rows.Count)
t5.Rows(2).Select()
word.Selection.InsertRowsBelow(1)
print("Rows after insert:", t5.Rows.Count)
doc.SaveAs(os.path.abspath(r'附件\test_insert5.doc'))
doc.Close(False)
word.Quit()
