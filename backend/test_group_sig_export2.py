import win32com.client, os, pythoncom, shutil

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件8.doc")
out_path = os.path.join(base_dir, "backend", "downloads", "test_group_sig_export2.doc")
if os.path.exists(out_path):
    try: os.remove(out_path)
    except: pass
shutil.copy(tpl, out_path)

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0

doc8 = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
t8 = doc8.Tables(1)

# Delete 5 default sample rows
for _ in range(5):
    try: t8.Rows(3).Delete()
    except: pass

group_rows = [
    {
        "cbfmc": "张三", "cbfbm": "3411241002000010001", "cbfbm_short": "0001", "lxdh": "1380001",
        "dkmc": "地块1", "dkbm_short": "01", "scmj": 2.5,
        "area_acknowledged": "X", "rights_correct": "", "bound_correct": "",
        "member_qualified": "", "self_verified": "", "self_signed": "",
        "satisfaction": "满意", "survey_method": "现场"
    },
    {
        "cbfmc": "张三", "cbfbm": "3411241002000010001", "cbfbm_short": "0001", "lxdh": "1380001",
        "dkmc": "地块2", "dkbm_short": "02", "scmj": 3.0,
        "area_acknowledged": "", "rights_correct": "", "bound_correct": "",
        "member_qualified": "", "self_verified": "", "self_signed": "",
        "satisfaction": "满意", "survey_method": "现场"
    },
    {
        "cbfmc": "李四", "cbfbm": "3411241002000010002", "cbfbm_short": "0002", "lxdh": "1380002",
        "dkmc": "地块3", "dkbm_short": "03", "scmj": 1.8,
        "area_acknowledged": "", "rights_correct": "X", "bound_correct": "",
        "member_qualified": "", "self_verified": "", "self_signed": "",
        "satisfaction": "满意", "survey_method": "电话"
    }
]

# Insert rows
for _ in range(max(0, len(group_rows) - 1)):
    t8.Rows(2).Select()
    word.Selection.InsertRowsBelow(1)

total_errors = 0
satisfaction_count = 0

for i, r in enumerate(group_rows):
    r_idx = i + 2
    farmer_name = r.get("cbfmc", "")
    
    check_keys = ["area_acknowledged", "rights_correct", "bound_correct", "member_qualified", "self_verified", "self_signed"]
    for k in check_keys:
        if r.get(k) == "X":
            total_errors += 1
            
    sat = r.get("satisfaction", "满意")
    if sat == "满意":
        satisfaction_count += 1
        
    t8.Cell(r_idx, 1).Range.Text = str(i + 1)
    t8.Cell(r_idx, 2).Range.Text = farmer_name
    t8.Cell(r_idx, 3).Range.Text = str(r.get("cbfbm_short", ""))
    t8.Cell(r_idx, 4).Range.Text = str(r.get("lxdh", ""))
    t8.Cell(r_idx, 5).Range.Text = str(r.get("dkmc", ""))
    t8.Cell(r_idx, 6).Range.Text = str(r.get("dkbm_short", ""))
    t8.Cell(r_idx, 7).Range.Text = str(r.get("scmj", ""))
    t8.Cell(r_idx, 8).Range.Text = r.get("area_acknowledged", "")
    t8.Cell(r_idx, 9).Range.Text = r.get("rights_correct", "")
    t8.Cell(r_idx, 10).Range.Text = r.get("bound_correct", "")
    t8.Cell(r_idx, 11).Range.Text = r.get("member_qualified", "")
    t8.Cell(r_idx, 12).Range.Text = r.get("self_verified", "")
    t8.Cell(r_idx, 13).Range.Text = r.get("self_signed", "")
    t8.Cell(r_idx, 14).Range.Text = sat
    t8.Cell(r_idx, 15).Range.Text = r.get("survey_method", "现场")
    t8.Cell(r_idx, 16).Range.Text = ""

# Fill Stats row FIRST before any vertical merging!
total_count = len(group_rows)
prog_score = max(20.0 - total_errors * 0.5, 0.0)
effect_score = (satisfaction_count / total_count * 10.0) if total_count > 0 else 10.0

r_stat_idx = total_count + 2
t8.Cell(r_stat_idx, 2).Range.Text = str(total_errors)
t8.Cell(r_stat_idx, 3).Range.Text = str(satisfaction_count)

r_score_idx = total_count + 3
t8.Cell(r_score_idx, 1).Range.Text = f"发包方程序规范得分=20-发包方错误总和({total_errors})×0.5={prog_score:.1f}；发包方工作成效（满意度调查）得分=满意数({satisfaction_count})/抽检数({total_count})×10={effect_score:.1f}"

# Now do vertical merge on Column 16 from bottom to top!
segments = []
curr_cbfbm = None
start_r = 2
for i, r in enumerate(group_rows):
    r_idx = i + 2
    cbfbm = str(r.get("cbfbm", "") or r.get("cbfbm_short", "") or r.get("cbfmc", ""))
    if cbfbm != curr_cbfbm:
        if curr_cbfbm is not None:
            segments.append((curr_cbfbm, start_r, r_idx - 1))
        curr_cbfbm = cbfbm
        start_r = r_idx
if curr_cbfbm is not None:
    segments.append((curr_cbfbm, start_r, len(group_rows) + 1))

sig_dir = os.path.join(base_dir, "backend", "uploads", "signatures")

for cbfbm, r_start, r_end in reversed(segments):
    if r_start < r_end:
        cell_start = t8.Cell(r_start, 16)
        cell_end = t8.Cell(r_end, 16)
        cell_start.Merge(cell_end)
        cell_target = cell_start
    else:
        cell_target = t8.Cell(r_start, 16)
        
    sig_path = os.path.join(sig_dir, f"{cbfbm}.png")
    if os.path.exists(sig_path):
        cell_target.Range.Text = ""
        pic = cell_target.Range.InlineShapes.AddPicture(
            FileName=os.path.abspath(sig_path), LinkToFile=False, SaveWithDocument=True
        )
        pic.Width = 65
        pic.Height = 26
        cell_target.Range.ParagraphFormat.Alignment = 1
        cell_target.VerticalAlignment = 1

doc8.SaveAs2(FileName=out_path, FileFormat=0)
doc8.Close(0)
word.Quit()
pythoncom.CoUninitialize()
print("Success! Merged signatures + statistics written cleanly.")