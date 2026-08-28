import win32com.client, os, pythoncom, shutil, time

def test_att7_new():
    t0 = time.time()
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件7.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "test_att7_new.doc")
    shutil.copy(tpl, out_path)
    
    doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
    t = doc.Tables(1)
    
    def format_score(val):
        if val is None or val == "": return ""
        f = float(val)
        if f.is_integer():
            return str(int(f))
        return f"{f:.1f}"

    def format_avg(val):
        if val is None: return ""
        return f"{float(val):.1f}"

    # Sample data matching the user's screenshot:
    # 全椒县: 12.5
    # 襄河镇: 9, 29, 12, 9, 59
    # 大墅镇: 14.5, 29.5, 14, 10, 68
    
    # 1. County row (Row 2)
    t.Rows(2).Cells(1).Range.Text = "1"
    t.Rows(2).Cells(2).Range.Text = "全椒县"
    t.Rows(2).Cells(3).Range.Text = "12.5"
    t.Rows(2).Cells(4).Range.Text = "/"
    t.Rows(2).Cells(5).Range.Text = "/"
    t.Rows(2).Cells(6).Range.Text = "/"
    t.Rows(2).Cells(7).Range.Text = "/"

    township_list = [
        ("341124100", "襄河镇", {"mech": 9.0, "prog": 29.0, "policy": 12.0, "effect": 9.0, "total": 59.0}),
        ("341124101", "古河镇", None),
        ("341124102", "大墅镇", {"mech": 14.5, "prog": 29.5, "policy": 14.0, "effect": 10.0, "total": 68.0}),
        ("341124103", "二郎口镇", None),
        ("341124104", "武岗镇", None),
        ("341124105", "马厂镇", None),
        ("341124106", "石沛镇", None),
        ("341124107", "十字镇", None),
        ("341124108", "西王镇", None),
        ("341124109", "六镇镇", None)
    ]
    
    sums = {"mech": 0.0, "prog": 0.0, "policy": 0.0, "effect": 0.0, "total": 0.0}
    count_eval = 0
    
    for idx, (code, name, sc) in enumerate(township_list):
        r_idx = idx + 3
        t.Rows(r_idx).Cells(1).Range.Text = str(idx + 2)
        t.Rows(r_idx).Cells(2).Range.Text = name
        if sc:
            count_eval += 1
            t.Rows(r_idx).Cells(3).Range.Text = format_score(sc["mech"])
            t.Rows(r_idx).Cells(4).Range.Text = format_score(sc["prog"])
            t.Rows(r_idx).Cells(5).Range.Text = format_score(sc["policy"])
            t.Rows(r_idx).Cells(6).Range.Text = format_score(sc["effect"])
            t.Rows(r_idx).Cells(7).Range.Text = format_score(sc["total"])
            for k in sums: sums[k] += sc[k]
        else:
            for c in range(3, 8):
                t.Rows(r_idx).Cells(c).Range.Text = ""

    # Row 13: 总评
    t.Rows(13).Cells(1).Range.Text = "12"
    t.Rows(13).Cells(2).Range.Text = "总评"
    if count_eval > 0:
        t.Rows(13).Cells(3).Range.Text = format_avg(sums["mech"] / count_eval)
        t.Rows(13).Cells(4).Range.Text = format_avg(sums["prog"] / count_eval)
        t.Rows(13).Cells(5).Range.Text = format_avg(sums["policy"] / count_eval)
        t.Rows(13).Cells(6).Range.Text = format_avg(sums["effect"] / count_eval)
        t.Rows(13).Cells(7).Range.Text = format_avg(sums["total"] / count_eval)
    else:
        for c in range(3, 8):
            t.Rows(13).Cells(c).Range.Text = ""

    with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\att7_new_res.txt", "w", encoding="utf-8") as out:
        for r in range(1, 14):
            vals = [t.Rows(r).Cells(c).Range.Text.strip().replace("\r","").replace("\x07","") for c in range(1, 8)]
            out.write(f"R{r}: {vals}\n")

    doc.SaveAs2(FileName=out_path, FileFormat=0)
    doc.Close(0)
    word.Quit()
    pythoncom.CoUninitialize()
    print(f"Att7 test finished in {time.time()-t0:.2f}s!")

test_att7_new()