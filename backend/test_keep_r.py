import win32com.client, os, pythoncom, shutil

def test_keep_r():
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件6.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "test_keep_r.doc")
    shutil.copy(tpl, out_path)
    
    doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
    
    t1 = doc.Tables(1)
    c4 = t1.Rows(2).Cells(4)
    raw = c4.Range.Text.replace("\x07", "")
    # Note: raw ends with \r
    modified = raw.replace("□未制定方案", "☑未制定方案").replace("□分工不明确", "☑分工不明确")
    # In Word, setting Range.Text to a string ending with \r will create a clean cell with internal \r
    # If it ends with \r, stripping just the last \r prevents an extra blank paragraph
    if modified.endswith("\r"):
        modified = modified[:-1]
        
    c4.Range.Text = modified
    
    with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\keep_r_res.txt", "w", encoding="utf-8") as out:
        out.write(f"T1 R2 C4 result:\n{repr(c4.Range.Text)}\n")
        out.write("Lines:\n")
        for line in c4.Range.Text.replace("\x07", "").split("\r"):
            out.write(f"  -> {line}\n")
        
    doc.SaveAs2(FileName=out_path, FileFormat=0)
    doc.Close(0)
    word.Quit()
    pythoncom.CoUninitialize()
    print("Keep R test finished successfully!")

test_keep_r()