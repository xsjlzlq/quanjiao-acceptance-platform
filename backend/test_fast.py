import win32com.client, os, pythoncom, shutil, time

def test_fast_fill():
    t0 = time.time()
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = False
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件6.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "test_fast_att6.doc")
    shutil.copy(tpl, out_path)
    
    doc = word.Documents.Open(out_path)
    print(f"Open took: {time.time() - t0:.2f}s")
    
    # Fast header replace via Find.Execute
    find = doc.Content.Find
    find.ClearFormatting()
    find.Replacement.ClearFormatting()
    find.Execute(
        FindText="行政区划名称：                             ",
        ReplaceWith="行政区划名称：襄河镇                    ",
        Replace=2 # 2 = wdReplaceAll
    )
    print(f"Header replace took: {time.time() - t0:.2f}s")

    doc.Save()
    doc.Close(False)
    word.Quit()
    pythoncom.CoUninitialize()
    print(f"Total time: {time.time() - t0:.2f}s")

test_fast_fill()