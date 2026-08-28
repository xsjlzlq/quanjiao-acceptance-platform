import os, time, shutil, re, win32com.client, pythoncom

def test_diag():
    print("1. CoInitialize")
    pythoncom.CoInitialize()
    
    print("2. DispatchEx Word")
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件6.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "diag_att6.doc")
    shutil.copy(tpl, out_path)
    
    print("3. Documents.Open")
    doc = word.Documents.Open(out_path)
    
    print("4. Find Replace Header")
    find = doc.Content.Find
    find.ClearFormatting()
    find.Replacement.ClearFormatting()
    find.Execute(
        FindText="行政区划名称：                             ",
        ReplaceWith="行政区划名称：全椒县                 ",
        Replace=2
    )
    
    print("5. Delete Tables")
    while doc.Tables.Count > 1:
        print("  Deleting table:", doc.Tables.Count)
        doc.Tables(doc.Tables.Count).Delete()
        
    print("6. Find Fuh")
    find_fuh = doc.Content.Find
    find_fuh.ClearFormatting()
    res = find_fuh.Execute(FindText="复核者：")
    print("  Find res:", res)
    if res:
        found_end = find_fuh.Parent.End
        print("  found_end:", found_end, "doc.Content.End:", doc.Content.End)
        if found_end < doc.Content.End:
            doc.Range(found_end, doc.Content.End).Delete()
            print("  Deleted after found_end")
            
    print("7. Save")
    doc.Save()
    print("8. Close")
    doc.Close(0)
    print("9. Quit")
    word.Quit()
    pythoncom.CoUninitialize()
    print("Done in total time!")

test_diag()