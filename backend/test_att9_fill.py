import win32com.client, os, pythoncom, shutil, time

def test_fill_att9():
    t0 = time.time()
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件9.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "test_att9_fill.doc")
    if os.path.exists(out_path):
        try: os.remove(out_path)
        except: pass
    shutil.copy(tpl, out_path)
    
    doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
    t = doc.Tables(1)
    
    # Mock groups data
    groups_list = [
        {
            "township": "襄河镇", "village": "邱塔村", "group": "第一组",
            "town_prog": 19.5, "town_effect": 9.5,
            "group_prog": 19.0, "group_effect": 10.0
        },
        {
            "township": "襄河镇", "village": "邱塔村", "group": "第二组",
            "town_prog": 19.5, "town_effect": 9.5,
            "group_prog": 20.0, "group_effect": 9.0
        },
        {
            "township": "大墅镇", "village": "大墅村", "group": "前头组",
            "town_prog": 18.5, "town_effect": 10.0,
            "group_prog": 18.5, "group_effect": 10.0
        }
    ]
    
    for idx, item in enumerate(groups_list):
        r_idx = idx + 3
        t.Cell(r_idx, 1).Range.Text = str(idx + 1)
        t.Cell(r_idx, 2).Range.Text = item["township"]
        t.Cell(r_idx, 3).Range.Text = f"{item['town_prog']:.1f}"
        t.Cell(r_idx, 4).Range.Text = f"{item['town_effect']:.1f}"
        t.Cell(r_idx, 5).Range.Text = item["village"]
        t.Cell(r_idx, 6).Range.Text = item["group"]
        t.Cell(r_idx, 7).Range.Text = f"{item['group_prog']:.1f}"
        t.Cell(r_idx, 8).Range.Text = f"{item['group_effect']:.1f}"

    # Clear remaining empty template rows if needed (row len(groups)+3 to 12)
    for r_idx in range(len(groups_list) + 3, 13):
        for c in range(1, 9):
            try: t.Cell(r_idx, c).Range.Text = ""
            except: pass

    with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\att9_test_fill_dump.txt", "w", encoding="utf-8") as out:
        for r in range(1, 13):
            cells = []
            for c in range(1, 9):
                try:
                    txt = t.Cell(r, c).Range.Text.strip().replace("\r", " ").replace("\x07", "")
                    cells.append(f"C{c}:{txt}")
                except: pass
            out.write(f"R{r}: " + " | ".join(cells) + "\n")

    doc.SaveAs2(FileName=out_path, FileFormat=0)
    doc.Close(0)
    word.Quit()
    pythoncom.CoUninitialize()
    print(f"Att9 fill test done in {time.time()-t0:.2f}s!")

test_fill_att9()