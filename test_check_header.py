import os
import win32com.client

word = win32com.client.DispatchEx('Word.Application')
doc = word.Documents.Open(os.path.abspath(r'附件\test_att8_header.doc'), ReadOnly=True)

try:
    print("P3:", repr(doc.Paragraphs(3).Range.Text))
    print("P4:", repr(doc.Paragraphs(4).Range.Text))
    t = doc.Tables(1)
    print("Table 1 cell 1,1:", repr(t.Cell(1,1).Range.Text))
except Exception as e:
    print("Error:", e)

doc.Close(False)
word.Quit()
