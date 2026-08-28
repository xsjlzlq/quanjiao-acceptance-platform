import os
import shutil

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend"
with open(os.path.join(base_dir, "test_new_exporter.py"), "r", encoding="utf-8") as f:
    neiye_code = f.read()

waiye_and_att4_5 = """
def export_att4(township_name):
    base_dir = os.path.abspath(r"G:\\全椒县二轮延包\\全椒县县级验收管理平台")
    os.makedirs(os.path.join(base_dir, 'backend', 'downloads'), exist_ok=True)
    template = os.path.join(base_dir, '附件', '附件4.doc')
    clean_ts = sanitize_filename(township_name)
    out = os.path.join(base_dir, 'backend', 'downloads', f'附件4_成果检查验收申请表_{clean_ts}.doc')
    if os.path.exists(out):
        try: os.remove(out)
        except: pass
    shutil.copy(template, out)
    return f"/api/download?file=downloads/附件4_成果检查验收申请表_{clean_ts}.doc"

def export_att5(stats_data, township_code, township_name):
    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx('Word.Application')
        word.Visible = False
        word.DisplayAlerts = 0
        
        base_dir = os.path.abspath(r"G:\\全椒县二轮延包\\全椒县县级验收管理平台")
        os.makedirs(os.path.join(base_dir, 'backend', 'downloads'), exist_ok=True)
        
        att5_template = os.path.join(base_dir, '附件', '附件5.doc')
        clean_ts = sanitize_filename(township_name)
        att5_out = os.path.join(base_dir, 'backend', 'downloads', f'附件5_抽样统计表_{clean_ts}.doc')
        if os.path.exists(att5_out):
            try: os.remove(att5_out)
            except: pass
        shutil.copy(att5_template, att5_out)
        
        doc5 = word.Documents.Open(FileName=att5_out, ReadOnly=False, ConfirmConversions=False)
        t5 = doc5.Tables(1)
        
        while t5.Rows.Count > 2:
            t5.Rows(3).Delete()
            
        for _ in range(max(0, len(stats_data) - 1)):
            t5.Rows(2).Select()
            word.Selection.InsertRowsBelow(1)
            
        for i, row in enumerate(stats_data):
            r_idx = i + 2
            try:
                t5.Cell(r_idx, 1).Range.Text = str(row.get('序号', ''))
                t5.Cell(r_idx, 2).Range.Text = str(row.get('乡镇名称', ''))
                t5.Cell(r_idx, 3).Range.Text = str(row.get('村名称', ''))
                t5.Cell(r_idx, 4).Range.Text = str(row.get('组名称', ''))
                t5.Cell(r_idx, 5).Range.Text = str(row.get('发包方总户数', ''))
                t5.Cell(r_idx, 6).Range.Text = str(row.get('抽样农户数5%', ''))
            except: pass
            
        doc5.SaveAs2(FileName=att5_out, FileFormat=0)
        doc5.Close(0)
        doc5 = None
        word.Quit()
        word = None
        return f"/api/download?file=downloads/附件5_抽样统计表_{clean_ts}.doc"
    except Exception as e:
        print("Export att5 error:", e)
        if word:
            try: word.Quit()
            except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()

def export_docs(stats_data, att8_data, township_code, township_name):
    url = export_att5(stats_data, township_code, township_name)
    return [url]

def export_waiye_att8(township_name, village_name, group_name, group_rows):
    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx('Word.Application')
        word.Visible = False
        word.DisplayAlerts = 0
        
        base_dir = os.path.abspath(r"G:\\全椒县二轮延包\\全椒县县级验收管理平台")
        tpl = os.path.join(base_dir, '附件', '附件8.doc')
        clean_ts = sanitize_filename(township_name)
        clean_vn = sanitize_filename(village_name)
        clean_gn = sanitize_filename(group_name)
        
        os.makedirs(os.path.join(base_dir, 'backend', 'downloads'), exist_ok=True)
        out_path = os.path.join(base_dir, 'backend', 'downloads', f'附件8_外业核查记录表_{clean_ts}{clean_vn}{clean_gn}.doc')
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        shutil.copy(tpl, out_path)
        
        doc8 = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
        p3 = doc8.Paragraphs(3)
        rng = p3.Range
        rng.End = rng.End - 1
        rng.Text = f"   乡镇：{township_name} \\t行政村：{village_name} \\t村民小组：{group_name}" + " "*30 + "2026 年    月    日"
        
        t8 = doc8.Tables(1)
        for _ in range(5):
            try: t8.Rows(3).Delete()
            except: pass
            
        for _ in range(max(0, len(group_rows) - 1)):
            t8.Rows(2).Select()
            word.Selection.InsertRowsBelow(1)
            
        total_errors = 0
        satisfaction_count = 0
        
        for i, r in enumerate(group_rows):
            r_idx = i + 2
            farmer_name = r.get('cbfmc', '') or r.get('承包方代表', '')
            
            check_keys = ['area_acknowledged', 'rights_correct', 'bound_correct', 'member_qualified', 'self_verified', 'self_signed']
            for k in check_keys:
                if r.get(k) == 'X':
                    total_errors += 1
            
            sat = r.get('satisfaction', '满意')
            if sat == '满意':
                satisfaction_count += 1
                
            t8.Cell(r_idx, 1).Range.Text = str(i + 1)
            t8.Cell(r_idx, 2).Range.Text = farmer_name
            t8.Cell(r_idx, 3).Range.Text = str(r.get('cbfbm_short', '') or r.get('承包方编码(缩略码)', ''))
            t8.Cell(r_idx, 4).Range.Text = str(r.get('lxdh', '') or r.get('联系电话', ''))
            t8.Cell(r_idx, 5).Range.Text = str(r.get('dkmc', '') or r.get('地块名称', ''))
            t8.Cell(r_idx, 6).Range.Text = str(r.get('dkbm_short', '') or r.get('地块简编码', ''))
            t8.Cell(r_idx, 7).Range.Text = str(r.get('scmj', '') or r.get('成果面积(亩)', ''))
            t8.Cell(r_idx, 8).Range.Text = r.get('area_acknowledged', '')
            t8.Cell(r_idx, 9).Range.Text = r.get('rights_correct', '')
            t8.Cell(r_idx, 10).Range.Text = r.get('bound_correct', '')
            t8.Cell(r_idx, 11).Range.Text = r.get('member_qualified', '')
            t8.Cell(r_idx, 12).Range.Text = r.get('self_verified', '')
            t8.Cell(r_idx, 13).Range.Text = r.get('self_signed', '')
            t8.Cell(r_idx, 14).Range.Text = sat
            t8.Cell(r_idx, 15).Range.Text = r.get('survey_method', r.get('调查抽样方式', '现场'))
            t8.Cell(r_idx, 16).Range.Text = ""

        # Fill stats rows BEFORE any vertical merges
        total_count = len(group_rows)
        prog_score = max(20.0 - total_errors * 0.5, 0.0)
        effect_score = (satisfaction_count / total_count * 10.0) if total_count > 0 else 10.0
        
        r_stat_idx = total_count + 2
        t8.Cell(r_stat_idx, 2).Range.Text = str(total_errors)
        t8.Cell(r_stat_idx, 3).Range.Text = str(satisfaction_count)
        
        r_score_idx = total_count + 3
        t8.Cell(r_score_idx, 1).Range.Text = f"发包方程序规范得分=20-发包方错误总和({total_errors})×0.5={prog_score:.1f}；发包方工作成效（满意度调查）得分=满意数({satisfaction_count})/抽检数({total_count})×10={effect_score:.1f}"

        # Group contiguous rows by contractor (cbfbm) and merge Column 16 from bottom to top
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
            else:
                cell_target.Range.Text = ""

        doc8.SaveAs2(FileName=out_path, FileFormat=0)
        doc8.Close(0)
        doc8 = None
        word.Quit()
        word = None
        return f"/api/download?file=downloads/附件8_外业核查记录表_{clean_ts}{clean_vn}{clean_gn}.doc"
    except Exception as e:
        print("Export waiye att8 error:", e)
        if word:
            try: word.Quit()
            except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()

def export_waiye_att9(samples_rows):
    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        
        base_dir = os.path.abspath(r"G:\\全椒县二轮延包\\全椒县县级验收管理平台")
        tpl = os.path.join(base_dir, "附件", "附件9.doc")
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_path = os.path.join(base_dir, "backend", "downloads", "附件9_全椒县县级自查外业组检查得分表.doc")
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        shutil.copy(tpl, out_path)
        
        doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
        t = doc.Tables(1)
        
        groups_map = defaultdict(list)
        for r in samples_rows:
            key = (r.get("township_name", ""), r.get("village_name", ""), r.get("group_name", ""))
            groups_map[key].append(r)
            
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
            
        township_avg = {}
        for t_name, items in township_groups.items():
            township_avg[t_name] = {
                "prog": sum(x["prog_score"] for x in items) / len(items),
                "effect": sum(x["effect_score"] for x in items) / len(items)
            }
            
        for idx, item in enumerate(group_stats):
            r_idx = idx + 3
            if r_idx > 12:
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
"""

full_code = neiye_code.strip() + "\n" + waiye_and_att4_5.strip() + "\n"
with open(os.path.join(base_dir, "doc_exporter.py"), "w", encoding="utf-8") as f:
    f.write(full_code)

import py_compile
py_compile.compile(os.path.join(base_dir, "doc_exporter.py"), doraise=True)
print("doc_exporter.py fully assembled and compiled!")
