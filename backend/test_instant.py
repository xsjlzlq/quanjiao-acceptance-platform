import win32com.client, os, pythoncom, shutil, time

def test_instant_trim():
    t0 = time.time()
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件6.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "test_instant.doc")
    shutil.copy(tpl, out_path)
    
    doc = word.Documents.Open(out_path)
    
    # 1. Delete tables
    while doc.Tables.Count > 1:
        doc.Tables(doc.Tables.Count).Delete()
        
    # 2. Find and trim
    find = doc.Content.Find
    find.ClearFormatting()
    if find.Execute(FindText="复核者："):
        found_end = find.Parent.End
        if found_end < doc.Content.End:
            doc.Range(found_end, doc.Content.End).Delete()
            
    doc.Save()
    doc.Close(0)
    word.Quit()
    pythoncom.CoUninitialize()
    print(f"Trimming 1/4 took: {time.time() - t0:.2f}s")

test_instant_trim()