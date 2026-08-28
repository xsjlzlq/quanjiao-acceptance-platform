import os
import win32com.client

word = win32com.client.DispatchEx('Word.Application')
doc = word.Documents.Open(os.path.abspath(r'附件\附件8.doc'))

rng = doc.Paragraphs(3).Range
rng.End = rng.End - 1
rng.Text = "   乡镇：襄河镇 \t行政村：八波村 \t村民小组：测试组" + " "*40 + "2026 年    月    日"

doc.SaveAs(os.path.abspath(r'附件\test_spacing.doc'))
doc.Close(False)
word.Quit()
