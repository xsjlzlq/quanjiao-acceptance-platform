import win32com.client, os, pythoncom, shutil, re

def sanitize_filename(name):
    clean = re.sub(r'[\\/*?:"<>|（）() ]', "", str(name)).strip()
    return clean if clean else "组"

def test_export_att8_custom():
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件8.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "test_att8_filled_custom.doc")
    if os.path.exists(out_path):
        try: os.remove(out_path)
        except: pass
    shutil.copy(tpl, out_path)
    
    doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
    
    township_name = "襄河镇"
    village_name = "邱塔村"
    group_name = "大庄组"
    
    # P3 header
    p3 = doc.Paragraphs(3)
    rng = p3.Range
    rng.End = rng.End - 1
    rng.Text = f"   乡镇：{township_name} \t行政村：{village_name} \t村民小组：{group_name}" + " "*30 + "2026 年    月    日"
    
    t = doc.Tables(1)
    
    # Delete initial sample rows 3..7 (rows 3, 4, 5, 6, 7)
    # Note: when row 3 is deleted, row 4 becomes row 3, etc.
    for _ in range(5):
        try: t.Rows(3).Delete()
        except: pass
        
    sample_rows = [
        {
            "cbfmc": "张三", "cbfbm_short": "0123", "lxdh": "13800000001",
            "dkmc": "门前田", "dkbm_short": "00101", "scmj": 2.35,
            "area_acknowledged": "", "rights_correct": "X", "bound_correct": "",
            "member_qualified": "", "self_verified": "", "self_signed": "",
            "satisfaction": "满意", "survey_method": "现场"
        },
        {
            "cbfmc": "李四", "cbfbm_short": "0124", "lxdh": "13800000002",
            "dkmc": "岗上地", "dkbm_short": "00102", "scmj": 3.10,
            "area_acknowledged": "X", "rights_correct": "", "bound_correct": "",
            "member_qualified": "", "self_verified": "X", "self_signed": "",
            "satisfaction": "满意", "survey_method": "电话"
        },
        {
            "cbfmc": "王五", "cbfbm_short": "0125", "lxdh": "13800000003",
            "dkmc": "塘角田", "dkbm_short": "00103", "scmj": 1.80,
            "area_acknowledged": "", "rights_correct": "", "bound_correct": "",
            "member_qualified": "", "self_verified": "", "self_signed": "",
            "satisfaction": "不满意", "survey_method": "现场"
        }
    ]
    
    # Insert rows if needed
    for _ in range(max(0, len(sample_rows) - 1)):
        t.Rows(2).Select()
        word.Selection.InsertRowsBelow(1)
        
    total_errors = 0
    satisfaction_count = 0
    unique_farmers = set()
    
    for i, r in enumerate(sample_rows):
        r_idx = i + 2
        farmer_name = r.get("cbfmc", "")
        unique_farmers.add(farmer_name)
        
        # Count errors in the 6 items
        row_errors = 0
        for k in ["area_acknowledged", "rights_correct", "bound_correct", "member_qualified", "self_verified", "self_signed"]:
            if r.get(k) == "X":
                row_errors += 1
        total_errors += row_errors
        
        if r.get("satisfaction") == "满意":
            satisfaction_count += 1
            
        t.Cell(r_idx, 1).Range.Text = str(i + 1)
        t.Cell(r_idx, 2).Range.Text = farmer_name
        t.Cell(r_idx, 3).Range.Text = str(r.get("cbfbm_short", ""))
        t.Cell(r_idx, 4).Range.Text = str(r.get("lxdh", ""))
        t.Cell(r_idx, 5).Range.Text = str(r.get("dkmc", ""))
        t.Cell(r_idx, 6).Range.Text = str(r.get("dkbm_short", ""))
        t.Cell(r_idx, 7).Range.Text = str(r.get("scmj", ""))
        t.Cell(r_idx, 8).Range.Text = r.get("area_acknowledged", "")
        t.Cell(r_idx, 9).Range.Text = r.get("rights_correct", "")
        t.Cell(r_idx, 10).Range.Text = r.get("bound_correct", "")
        t.Cell(r_idx, 11).Range.Text = r.get("member_qualified", "")
        t.Cell(r_idx, 12).Range.Text = r.get("self_verified", "")
        t.Cell(r_idx, 13).Range.Text = r.get("self_signed", "")
        t.Cell(r_idx, 14).Range.Text = r.get("satisfaction", "满意")
        t.Cell(r_idx, 15).Range.Text = r.get("survey_method", "现场")
        t.Cell(r_idx, 16).Range.Text = ""

    # Stats rows
    total_farmers = len(unique_farmers) if unique_farmers else len(sample_rows)
    prog_score = max(20.0 - total_errors * 0.5, 0.0)
    effect_score = (satisfaction_count / len(sample_rows) * 10.0) if sample_rows else 10.0
    
    # Row len(sample_rows) + 2 is Row 8 (error stats)
    r_stat_idx = len(sample_rows) + 2
    t.Rows(r_stat_idx).Cells(2).Range.Text = str(total_errors)
    t.Rows(r_stat_idx).Cells(3).Range.Text = str(satisfaction_count)
    
    # Row len(sample_rows) + 3 is Row 9 (formula & score)
    r_score_idx = len(sample_rows) + 3
    t.Rows(r_score_idx).Cells(1).Range.Text = f"发包方程序规范得分=20-发包方错误总和({total_errors})×0.5={prog_score:.1f}；发包方工作成效（满意度调查）得分=满意数({satisfaction_count})/抽检数({len(sample_rows)})×10={effect_score:.1f}"

    doc.SaveAs2(FileName=out_path, FileFormat=0)
    doc.Close(0)
    word.Quit()
    pythoncom.CoUninitialize()
    print("test_export_att8_custom finished successfully!")

test_export_att8_custom()