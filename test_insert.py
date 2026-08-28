import os
import win32com.client

word = win32com.client.DispatchEx('Word.Application')
word.Visible = False
doc = word.Documents.Open(os.path.abspath(r'附件\附件8.doc'))
t8 = doc.Tables(1)

for _ in range(5):
    t8.Rows(3).Delete()

# Now row 2 is the only data row.
# Let's add 2 more rows.
for _ in range(2):
    t8.Rows(2).Select()
    word.Selection.InsertRowsBelow(1)

# Verify count
print("Total rows:", t8.Rows.Count) # should be 3 data + 2 footers = 5

doc.SaveAs(os.path.abspath(r'附件\test_insert.doc'))
doc.Close(False)
word.Quit()
