import win32com.client, os, pythoncom, shutil

def test_header_replace():
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件6.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "test_header_exact.doc")
    shutil.copy(tpl, out_path)
    
    doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
    
    township_name = "襄河镇"
    full_name = "全椒县" + township_name if not township_name.startswith("全椒县") else township_name
    
    for p in doc.Paragraphs:
        t = p.Range.Text
        if "行政区划名称" in t:
            for c_name in ["机制运行", "程序规范", "政策落实", "工作成效"]:
                if c_name in t:
                    # In template: 行政区划名称：                             验收内容：机制运行                            2026 年       月      日
                    new_text = f"行政区划名称：{full_name:<16}  验收内容：{c_name:<16}  2026 年       月      日\r"
                    p.Range.Text = new_text
                    break
                    
    # Let's check paragraph texts now
    with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\header_exact_res.txt", "w", encoding="utf-8") as out:
        for i in range(1, doc.Paragraphs.Count + 1):
            txt = doc.Paragraphs(i).Range.Text.strip().replace("\r", "").replace("\x07", "")
            if "行政区划名称" in txt:
                out.write(f"P{i}: {txt}\n")
                
    doc.SaveAs2(FileName=out_path, FileFormat=0)
    doc.Close(0)
    word.Quit()
    pythoncom.CoUninitialize()
    print("Header exact test finished successfully!")

test_header_replace()