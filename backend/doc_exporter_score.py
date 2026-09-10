import os
import shutil
import pythoncom
import win32com.client
from doc_exporter import replace_common_bookmarks
from database import get_base_dir

def format_score(score):
    if score is None:
        return ""
    if isinstance(score, (int, float)):
        if score == int(score):
            return str(int(score))
        return f"{score:.1f}"
    return str(score)

def export_att10(township_scores, county_mech):
    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        from database import get_county_and_townships_sync
        county_info, township_list_raw = get_county_and_townships_sync()
        county_name = county_info.get("name", "全椒县")
        township_list = [item["name"] for item in township_list_raw]

        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        
        base_dir = get_base_dir()
        tpl = os.path.join(base_dir, "附件", "附件10.doc")
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_filename = f"附件10_{county_name}县级自查得分汇总表.doc"
        out_path = os.path.join(base_dir, "backend", "downloads", out_filename)
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        shutil.copy(tpl, out_path)
        
        doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
        replace_common_bookmarks(doc, county_name)
        t = doc.Tables(1)
        
        N = len(township_list)
        # 表格初始结构：Row 1 和 2 是表头，最后一行是县级汇总行，中间预留行数 = t.Rows.Count - 3
        current_reserved = t.Rows.Count - 3
        if N > current_reserved:
            # 在最后一个乡镇行后插入 N - current_reserved 行
            last_ts_row = t.Rows.Count - 1
            t.Cell(last_ts_row, 1).Select()
            word.Selection.InsertRowsBelow(N - current_reserved)
        elif N < current_reserved:
            # 删除多余行
            for _ in range(current_reserved - N):
                del_row = t.Rows.Count - 1
                t.Cell(del_row, 1).Select()
                word.Selection.Rows.Delete()
        
        for idx, t_name in enumerate(township_list):
            r_idx = idx + 3
            sc = township_scores.get(t_name, None)
            
            t.Cell(r_idx, 1).Range.Text = str(idx + 1)
            t.Cell(r_idx, 2).Range.Text = t_name
            if sc:
                t.Cell(r_idx, 3).Range.Text = format_score(sc["mech"])
                t.Cell(r_idx, 4).Range.Text = format_score(sc["prog_nei"])
                t.Cell(r_idx, 5).Range.Text = format_score(sc["prog_wai"])
                t.Cell(r_idx, 6).Range.Text = format_score(sc["policy"])
                t.Cell(r_idx, 7).Range.Text = format_score(sc["effect_nei"])
                t.Cell(r_idx, 8).Range.Text = format_score(sc["effect_wai"])
                t.Cell(r_idx, 9).Range.Text = format_score(sc["total"])
            else:
                for c in range(3, 10):
                    t.Cell(r_idx, c).Range.Text = ""
                    
        # Summary Row (County)
        county_row = t.Rows.Count
        count_evaluated = len([sc for sc in township_scores.values() if sc])
        if count_evaluated > 0:
            avg_mech = round((sum(sc["mech"] for sc in township_scores.values() if sc) + county_mech) / (count_evaluated + 1), 1)
            avg_prog_nei = sum(sc["prog_nei"] for sc in township_scores.values() if sc) / count_evaluated
            avg_prog_wai = sum(sc["prog_wai"] for sc in township_scores.values() if sc) / count_evaluated
            avg_policy = round(sum(sc["policy"] for sc in township_scores.values() if sc) / count_evaluated, 1)
            avg_effect_nei = sum(sc["effect_nei"] for sc in township_scores.values() if sc) / count_evaluated
            avg_effect_wai = sum(sc["effect_wai"] for sc in township_scores.values() if sc) / count_evaluated
            avg_prog = round(avg_prog_nei + avg_prog_wai, 1)
            avg_effect = round(avg_effect_nei + avg_effect_wai, 1)
            avg_total = round(avg_mech + avg_prog + avg_policy + avg_effect, 1)
        else:
            avg_mech = county_mech
            avg_prog = 50.0
            avg_policy = 15.0
            avg_effect = 20.0
            avg_total = avg_mech + avg_prog + avg_policy + avg_effect

        t.Cell(county_row, 1).Range.Text = str(N + 1)
        t.Cell(county_row, 2).Range.Text = county_name
        t.Cell(county_row, 3).Range.Text = format_score(avg_mech)
        t.Cell(county_row, 4).Range.Text = format_score(avg_prog)
        t.Cell(county_row, 5).Range.Text = format_score(avg_policy)
        t.Cell(county_row, 6).Range.Text = format_score(avg_effect)
        t.Cell(county_row, 7).Range.Text = format_score(avg_total)
            
        doc.SaveAs2(FileName=out_path, FileFormat=0)
        doc.Close(0)
        doc = None
        word.Quit()
        word = None
        return f"/api/download?file=downloads/{out_filename}"
    except Exception as e:
        print("export_att10 error:", e)
        if doc:
            try: doc.Close(0)
            except: pass
        if word:
            try: word.Quit()
            except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()

def export_att11(county_avg, special1, special2, special3, final_score):
    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        from database import get_county_and_townships_sync
        county_info, _ = get_county_and_townships_sync()
        county_name = county_info.get("name", "全椒县")

        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        
        base_dir = get_base_dir()
        tpl = os.path.join(base_dir, "附件", "附件11.doc")
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_filename = f"附件11_{county_name}县级自查验收评定表.doc"
        out_path = os.path.join(base_dir, "backend", "downloads", out_filename)
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        shutil.copy(tpl, out_path)
        
        doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
        replace_common_bookmarks(doc, county_name)
        t = doc.Tables(1)
        
        t.Cell(2, 4).Range.Text = format_score(round(county_avg.get("mech", 15.0), 1))
        t.Cell(3, 4).Range.Text = format_score(round(county_avg.get("prog_nei", 30.0) + county_avg.get("prog_wai", 20.0), 1))
        t.Cell(4, 4).Range.Text = format_score(round(county_avg.get("policy", 15.0), 1))
        
        
        effect_score = round(county_avg.get("effect_nei", 10.0) + county_avg.get("effect_wai", 10.0), 1)
        deduct_total = (0.5 if special1 else 0.0) + (1.0 if special2 else 0.0) + special3
        if deduct_total > 0:
            effect_score -= deduct_total
            
        rng_cell = t.Cell(5, 5).Range
        cell_text = rng_cell.Text
        if cell_text.endswith('\r\x07'):
            cell_text = cell_text[:-2]
            
        if special1:
            cell_text = cell_text.replace('□对落实省市级验收方案要求不严格的', '☑对落实省市级验收方案要求不严格的')
        if special2:
            cell_text = cell_text.replace('□对落实省市级验收方案要求走过场', '☑对落实省市级验收方案要求走过场')
        if special3 > 0:
            cell_text = cell_text.replace('□对存在整组未延包的', '☑对存在整组未延包的')
            cell_text = cell_text.replace('扣0.5-1分。', f'扣0.5-1分。（实际扣除：{special3}分）。')
            
        rng_cell.Text = cell_text
            
        t.Cell(5, 4).Range.Text = format_score(effect_score)
        
        t.Cell(6, 2).Range.Text = format_score(final_score)
        
        if final_score >= 90: 
            check_level = '优秀'
            accept_level = '合格'
        elif final_score >= 80: 
            check_level = '良好'
            accept_level = '合格'
        elif final_score >= 70: 
            check_level = '合格'
            accept_level = '合格'
        else: 
            check_level = '不合格'
            accept_level = '不合格'
            
        find = doc.Content.Find
        find.ClearFormatting()
        find.Text = '检查结果评定为：'
        find.Execute()
        if find.Found:
            rng = find.Parent
            rng.Collapse(0) # wdCollapseEnd
            rng.MoveEndUntil('，')
            rng.Text = f'  {check_level}  '
            rng.Font.Underline = 1
            
        find = doc.Content.Find
        find.ClearFormatting()
        find.Text = '验收结果评定为'
        find.Execute()
        if find.Found:
            rng = find.Parent
            rng.Collapse(0)
            rng.MoveEndUntil('。')
            rng.Text = f'  {accept_level}  '
            rng.Font.Underline = 1
        
        doc.SaveAs2(FileName=out_path, FileFormat=0)
        doc.Close(0)
        doc = None
        word.Quit()
        word = None
        return f"/api/download?file=downloads/{out_filename}"
    except Exception as e:
        print("export_att11 error:", e)
        if doc:
            try: doc.Close(0)
            except: pass
        if word:
            try: word.Quit()
            except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()