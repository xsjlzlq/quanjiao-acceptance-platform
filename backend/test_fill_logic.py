import win32com.client, os, pythoncom, shutil

def test_fill_att6():
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件6.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "test_att6_filled.doc")
    shutil.copy(tpl, out_path)
    
    doc = word.Documents.Open(out_path)
    
    # Replace header info in all paragraphs
    for p in doc.Paragraphs:
        txt = p.Range.Text
        if "行政区划名称：" in txt:
            # Replace whitespace between 行政区划名称： and 验收内容：
            p.Range.Find.Execute(
                FindText="行政区划名称：                             ",
                ReplaceWith="行政区划名称：襄河镇                    ",
                Replace=1
            )
    
    t1 = doc.Tables(1)
    # Checkbox replacement test in Table 1
    # R2: 配套延包政策文件
    cell4 = t1.Rows(2).Cells(4)
    # Suppose "未制定方案" and "分工不明确" are checked
    txt = cell4.Range.Text
    txt = txt.replace("□未制定方案", "☑未制定方案").replace("□分工不明确", "☑分工不明确")
    # Clean trailing Word cell markers when setting text
    cell4.Range.Text = txt.replace("\x07", "")
    t1.Rows(2).Cells(6).Range.Text = "2"
    
    # R6: 总计扣分
    t1.Rows(6).Cells(3).Range.Text = "2"
    # R7: 重要问题描述
    t1.Rows(7).Cells(2).Range.Text = "1. 未制定延包方案；2. 职责分工不明确。"
    
    doc.Save()
    doc.Close(False)
    word.Quit()
    pythoncom.CoUninitialize()
    print("Table 1 filled successfully!")

test_fill_att6()