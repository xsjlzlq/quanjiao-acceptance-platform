import win32com.client, os, pythoncom, shutil

def test_inplace_replace():
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件6.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "test_newlines.doc")
    shutil.copy(tpl, out_path)
    
    doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
    t1 = doc.Tables(1)
    
    # Method 1: replace keeping \r
    c4 = t1.Rows(2).Cells(4)
    raw = c4.Range.Text.replace("\x07", "")
    print("Original lines:", raw.split("\r"))
    modified = raw.replace("□未制定方案", "☑未制定方案").replace("□分工不明确", "☑分工不明确")
    c4.Range.Text = modified
    
    # Check what Word has now
    print("After setting text:", repr(c4.Range.Text))
    
    doc.SaveAs2(FileName=out_path, FileFormat=0)
    doc.Close(0)
    word.Quit()
    pythoncom.CoUninitialize()
    print("Inplace replace test finished!")

test_inplace_replace()