import os, sys, shutil, re, win32com.client, pythoncom
from collections import defaultdict

def sanitize_filename(name):
    clean = re.sub(r'[\\/*?:"<>|（）() ]', "", str(name)).strip()
    return clean if clean else "乡镇"

def format_score(val):
    if val is None or val == "": return ""
    f = float(val)
    if f.is_integer():
        return str(int(f))
    return f"{f:.1f}"

def export_waiye_att9(samples_rows):
    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        
        base_dir = os.path.abspath(r"G:\全椒县二轮延包\全椒县县级验收管理平台")
        tpl = os.path.join(base_dir, "附件", "附件9.doc")
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_path = os.path.join(base_dir, "backend", "downloads", "附件9_全椒县县级自查外业组检查得分表.doc")
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        shutil.copy(tpl, out_path)
        
        doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
        t = doc.Tables(1)
        
        # 1. Group records by (township, village, group)
        groups_map = defaultdict(list)
        for r in samples_rows:
            key = (r.get("township_name", ""), r.get("village_name", ""), r.get("group_name", ""))
            groups_map[key].append(r)
            
        # 2. Calculate group scores and township aggregates
        group_stats = []
        township_groups = defaultdict(list)
        
        for (t_name, v_name, g_name), g_rows in groups_map.items():
            total_errors = 0
            satisfaction_count = 0
            for r in g_rows:
                for k in ["area_acknowledged", "rights_correct", "bound_correct", "member_qualified", "self_verified", "self_signed"]:
                    if r.get(k) == "X":
                        total_errors += 1
                if r.get("satisfaction") == "满意":
                    satisfaction_count += 1
                    
            tot_cnt = len(g_rows)
            prog_score = max(20.0 - total_errors * 0.5, 0.0)
            effect_score = (satisfaction_count / tot_cnt * 10.0) if tot_cnt > 0 else 10.0
            
            item = {
                "township": t_name,
                "village": v_name,
                "group": g_name,
                "prog_score": prog_score,
                "effect_score": effect_score
            }
            group_stats.append(item)
            township_groups[t_name].append(item)
            
        # 3. Calculate township average scores
        township_avg = {}
        for t_name, items in township_groups.items():
            township_avg[t_name] = {
                "prog": sum(x["prog_score"] for x in items) / len(items),
                "effect": sum(x["effect_score"] for x in items) / len(items)
            }
            
        # 4. Fill Table 1
        for idx, item in enumerate(group_stats):
            r_idx = idx + 3
            if r_idx > 12:
                # If more than 10 groups, insert rows
                t.Rows(12).Select()
                word.Selection.InsertRowsBelow(1)
                
            t_avg = township_avg.get(item["township"], {"prog": 20.0, "effect": 10.0})
            
            t.Cell(r_idx, 1).Range.Text = str(idx + 1)
            t.Cell(r_idx, 2).Range.Text = item["township"]
            t.Cell(r_idx, 3).Range.Text = format_score(t_avg["prog"])
            t.Cell(r_idx, 4).Range.Text = format_score(t_avg["effect"])
            t.Cell(r_idx, 5).Range.Text = item["village"]
            t.Cell(r_idx, 6).Range.Text = item["group"]
            t.Cell(r_idx, 7).Range.Text = format_score(item["prog_score"])
            t.Cell(r_idx, 8).Range.Text = format_score(item["effect_score"])

        # Clear remaining empty template rows if fewer than 10 groups
        for r_idx in range(len(group_stats) + 3, 13):
            for c in range(1, 9):
                try: t.Cell(r_idx, c).Range.Text = ""
                except: pass

        doc.SaveAs2(FileName=out_path, FileFormat=0)
        doc.Close(0)
        doc = None
        word.Quit()
        word = None
        return "/api/download?file=downloads/附件9_全椒县县级自查外业组检查得分表.doc"
    except Exception as e:
        print("export_waiye_att9 error:", e)
        if doc:
            try: doc.Close(0)
            except: pass
        if word:
            try: word.Quit()
            except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()

# Test with sample rows
mock_samples = [
    {
        "township_name": "襄河镇", "village_name": "邱塔村", "group_name": "第一组",
        "area_acknowledged": "X", "rights_correct": "", "bound_correct": "",
        "member_qualified": "", "self_verified": "", "self_signed": "",
        "satisfaction": "满意", "survey_method": "现场"
    },
    {
        "township_name": "襄河镇", "village_name": "邱塔村", "group_name": "第二组",
        "area_acknowledged": "", "rights_correct": "", "bound_correct": "",
        "member_qualified": "", "self_verified": "", "self_signed": "",
        "satisfaction": "满意", "survey_method": "现场"
    },
    {
        "township_name": "大墅镇", "village_name": "大墅村", "group_name": "前头组",
        "area_acknowledged": "X", "rights_correct": "X", "bound_correct": "",
        "member_qualified": "", "self_verified": "", "self_signed": "",
        "satisfaction": "不满意", "survey_method": "现场"
    }
]

url = export_waiye_att9(mock_samples)
print("Att9 generated url:", url)