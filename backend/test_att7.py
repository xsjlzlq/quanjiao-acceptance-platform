import win32com.client, os, pythoncom, shutil, time

def test_fill_att7():
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = False
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件7.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "test_att7_filled.doc")
    shutil.copy(tpl, out_path)
    
    doc = word.Documents.Open(out_path)
    t = doc.Tables(1)
    
    # 1. County row (Row 2)
    t.Rows(2).Cells(2).Range.Text = "全椒县"
    t.Rows(2).Cells(3).Range.Text = "13.5"
    t.Rows(2).Cells(4).Range.Text = "/"
    t.Rows(2).Cells(5).Range.Text = "/"
    t.Rows(2).Cells(6).Range.Text = "/"
    t.Rows(2).Cells(7).Range.Text = "13.5"
    
    # 2. Township rows (Row 3 to 12)
    townships = [
        "襄河镇", "古河镇", "大墅镇", "二郎口镇", "武岗镇",
        "马厂镇", "石沛镇", "十字镇", "西王镇", "六镇镇"
    ]
    
    for idx, name in enumerate(townships):
        r_idx = idx + 3
        t.Rows(r_idx).Cells(1).Range.Text = str(idx + 2)
        t.Rows(r_idx).Cells(2).Range.Text = name
        # fill sample scores
        t.Rows(r_idx).Cells(3).Range.Text = "14.0"
        t.Rows(r_idx).Cells(4).Range.Text = "28.5"
        t.Rows(r_idx).Cells(5).Range.Text = "14.0"
        t.Rows(r_idx).Cells(6).Range.Text = "9.0"
        t.Rows(r_idx).Cells(7).Range.Text = "65.5"

    # 3. 总评 (Row 13)
    t.Rows(13).Cells(1).Range.Text = "12"
    t.Rows(13).Cells(2).Range.Text = "总评"
    t.Rows(13).Cells(3).Range.Text = "14.0"
    t.Rows(13).Cells(4).Range.Text = "28.5"
    t.Rows(13).Cells(5).Range.Text = "14.0"
    t.Rows(13).Cells(6).Range.Text = "9.0"
    t.Rows(13).Cells(7).Range.Text = "65.5"

    doc.Save()
    doc.Close(False)
    word.Quit()
    pythoncom.CoUninitialize()
    print("Att7 filled successfully!")

test_fill_att7()