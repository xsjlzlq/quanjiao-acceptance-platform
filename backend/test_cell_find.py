import win32com.client, os, pythoncom, shutil

def test_cell_find():
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件6.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "test_cell_find.doc")
    shutil.copy(tpl, out_path)
    
    doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
    
    # Global find & replace across doc.Content
    def check_box(target_text, replacement_text=None):
        if replacement_text is None:
            replacement_text = target_text.replace("□", "☑")
        find = doc.Content.Find
        find.ClearFormatting()
        find.Replacement.ClearFormatting()
        find.Execute(
            FindText=target_text,
            ReplaceWith=replacement_text,
            Replace=1 # wdReplaceOne
        )
    
    # Test checking boxes
    check_box("□未制定方案")
    check_box("□分工不明确")
    check_box("□未保障特殊群体权益", "☑未保障特殊群体权益（2起）")
    
    # Let's inspect the raw text of Table 1 Row 2 C4 and Table 3 Row 3 C4
    with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\cell_find_res.txt", "w", encoding="utf-8") as out:
        t1 = doc.Tables(1)
        out.write(f"T1 R2 C4:\n{repr(t1.Rows(2).Cells(4).Range.Text)}\n")
        t3 = doc.Tables(3)
        out.write(f"T3 R3 C4:\n{repr(t3.Rows(3).Cells(4).Range.Text)}\n")
        
    doc.SaveAs2(FileName=out_path, FileFormat=0)
    doc.Close(0)
    word.Quit()
    pythoncom.CoUninitialize()
    print("Test finished successfully!")

test_cell_find()