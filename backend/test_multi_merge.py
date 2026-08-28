import win32com.client, os, pythoncom, shutil

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件8.doc")
out_path = os.path.join(base_dir, "backend", "downloads", "test_multi_merge.doc")
if os.path.exists(out_path):
    try: os.remove(out_path)
    except: pass
shutil.copy(tpl, out_path)

doc8 = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
t8 = doc8.Tables(1)

# Delete 5 default sample rows
for _ in range(5):
    try: t8.Rows(3).Delete()
    except: pass

# Suppose we have:
# Farmer 1 (2 parcels): row 2, 3
# Farmer 2 (1 parcel): row 4
# Farmer 3 (3 parcels): row 5, 6, 7
# Total 6 rows -> insert 5 rows below Row 2
for _ in range(5):
    t8.Rows(2).Select()
    word.Selection.InsertRowsBelow(1)

data = [
    {"name": "张三", "cbfbm": "1001", "dk": "地块1"},
    {"name": "张三", "cbfbm": "1001", "dk": "地块2"},
    {"name": "李四", "cbfbm": "1002", "dk": "地块3"},
    {"name": "王五", "cbfbm": "1003", "dk": "地块4"},
    {"name": "王五", "cbfbm": "1003", "dk": "地块5"},
    {"name": "王五", "cbfbm": "1003", "dk": "地块6"},
]

# 1. Fill all text in all rows FIRST before any merges
for i, d in enumerate(data):
    r_idx = i + 2
    t8.Cell(r_idx, 1).Range.Text = str(i + 1)
    t8.Cell(r_idx, 2).Range.Text = d["name"]
    t8.Cell(r_idx, 5).Range.Text = d["dk"]

# 2. Find contiguous segments for each cbfbm
segments = [] # list of (cbfbm, r_start, r_end)
curr_cbfbm = None
start_r = 2
for i, d in enumerate(data):
    r_idx = i + 2
    if d["cbfbm"] != curr_cbfbm:
        if curr_cbfbm is not None:
            segments.append((curr_cbfbm, start_r, r_idx - 1))
        curr_cbfbm = d["cbfbm"]
        start_r = r_idx
if curr_cbfbm is not None:
    segments.append((curr_cbfbm, start_r, len(data) + 1))

print("Contractor row segments:", segments)

# 3. Process merges and image insertion in REVERSE order (bottom to top) to prevent coordinate shifts!
sig_path = os.path.abspath(os.path.join(base_dir, "backend", "uploads", "signatures", "test_sig_0123.png"))

for cbfbm, r_start, r_end in reversed(segments):
    print(f"Processing cbfbm {cbfbm} (rows {r_start} to {r_end})...")
    if r_start < r_end:
        # Merge column 16 from r_start to r_end
        cell_start = t8.Cell(r_start, 16)
        cell_end = t8.Cell(r_end, 16)
        cell_start.Merge(cell_end)
        cell_target = cell_start
    else:
        cell_target = t8.Cell(r_start, 16)
        
    # Insert image
    if os.path.exists(sig_path):
        cell_target.Range.Text = ""
        pic = cell_target.Range.InlineShapes.AddPicture(FileName=sig_path, LinkToFile=False, SaveWithDocument=True)
        pic.Width = 65
        pic.Height = 26
        cell_target.Range.ParagraphFormat.Alignment = 1
        cell_target.VerticalAlignment = 1

doc8.SaveAs2(FileName=out_path, FileFormat=0)
doc8.Close(0)
word.Quit()
pythoncom.CoUninitialize()
print("Multiple segments bottom-to-top merge test finished successfully!")