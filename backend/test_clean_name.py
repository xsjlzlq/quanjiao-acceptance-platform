import win32com.client, os, pythoncom, shutil, time

def test_ascii_name():
    t0 = time.time()
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件6.doc")
    # Test with standard name without fullwidth brackets
    out_path = os.path.join(base_dir, "backend", "downloads", "附件6_全椒县县级自查内业组检查记录表_1_4.doc")
    if os.path.exists(out_path):
        try: os.remove(out_path)
        except: pass
    shutil.copy(tpl, out_path)
    
    doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
    
    while doc.Tables.Count > 1:
        doc.Tables(doc.Tables.Count).Delete()
        
    find_fuh = doc.Content.Find
    find_fuh.ClearFormatting()
    if find_fuh.Execute(FindText="复核者："):
        found_end = find_fuh.Parent.End
        if found_end < doc.Content.End:
            doc.Range(found_end, doc.Content.End).Delete()
            
    doc.SaveAs2(FileName=out_path, FileFormat=0)
    doc.Close(0)
    word.Quit()
    pythoncom.CoUninitialize()
    print(f"Export with clean filename took: {time.time()-t0:.2f}s")

test_ascii_name()