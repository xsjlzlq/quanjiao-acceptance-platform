with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\doc_exporter.py", "r", encoding="utf-8") as f:
    code = f.read()

old_func_start = code.find("def export_waiye_att8(township_name, village_name, group_name, group_rows):")
old_func_end = code.find("def export_waiye_att9(samples_rows):")

new_func = """def export_waiye_att8(township_name, village_name, group_name, group_rows):
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

"""

code = code[:old_func_start] + new_func + code[old_func_end:]

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\doc_exporter.py", "w", encoding="utf-8") as f:
    f.write(code)

import py_compile
py_compile.compile(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\doc_exporter.py", doraise=True)
print("doc_exporter.py updated with signature merge support.")