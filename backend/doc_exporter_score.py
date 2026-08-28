import os
import shutil
import pythoncom
import win32com.client

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
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        
        base_dir = os.path.abspath(r"G:\全椒县二轮延包\全椒县县级验收管理平台")
        tpl = os.path.join(base_dir, "附件", "附件10.doc")
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_path = os.path.join(base_dir, "backend", "downloads", "附件10_全椒县县级自查得分汇总表.doc")
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        shutil.copy(tpl, out_path)
        
        doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
        t = doc.Tables(1)
        
        township_list = [
            "襄河镇", "古河镇", "大墅镇", "二郎口镇", "武岗镇",
            "马厂镇", "石沛镇", "十字镇", "西王镇", "六镇镇"
        ]
        
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
                    
        # Row 13 is the County
        count_evaluated = len([sc for sc in township_scores.values() if sc])
        if count_evaluated > 0:
            avg_mech = (sum(sc["mech"] for sc in township_scores.values() if sc) + county_mech) / (count_evaluated + 1)
            avg_prog_nei = sum(sc["prog_nei"] for sc in township_scores.values() if sc) / count_evaluated
            avg_prog_wai = sum(sc["prog_wai"] for sc in township_scores.values() if sc) / count_evaluated
            avg_policy = sum(sc["policy"] for sc in township_scores.values() if sc) / count_evaluated
            avg_effect_nei = sum(sc["effect_nei"] for sc in township_scores.values() if sc) / count_evaluated
            avg_effect_wai = sum(sc["effect_wai"] for sc in township_scores.values() if sc) / count_evaluated
            avg_total = avg_mech + avg_prog_nei + avg_prog_wai + avg_policy + avg_effect_nei + avg_effect_wai
            
            avg_prog = avg_prog_nei + avg_prog_wai
            avg_effect = avg_effect_nei + avg_effect_wai
        else:
            avg_mech = county_mech
            avg_prog = 50.0
            avg_policy = 15.0
            avg_effect = 20.0
            avg_total = avg_mech + avg_prog + avg_policy + avg_effect

        t.Cell(13, 1).Range.Text = "11"
        t.Cell(13, 2).Range.Text = "全椒县"
        t.Cell(13, 3).Range.Text = format_score(avg_mech)
        t.Cell(13, 4).Range.Text = format_score(avg_prog)
        t.Cell(13, 5).Range.Text = format_score(avg_policy)
        t.Cell(13, 6).Range.Text = format_score(avg_effect)
        t.Cell(13, 7).Range.Text = format_score(avg_total)
            
        doc.SaveAs2(FileName=out_path, FileFormat=0)
        doc.Close(0)
        doc = None
        word.Quit()
        word = None
        return "/api/download?file=downloads/附件10_全椒县县级自查得分汇总表.doc"
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
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        
        base_dir = os.path.abspath(r"G:\全椒县二轮延包\全椒县县级验收管理平台")
        tpl = os.path.join(base_dir, "附件", "附件11.doc")
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_path = os.path.join(base_dir, "backend", "downloads", "附件11_全椒县县级自查验收评定表.doc")
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        shutil.copy(tpl, out_path)
        
        doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
        t = doc.Tables(1)
        
        t.Cell(2, 4).Range.Text = format_score(county_avg.get("mech", 15.0))
        t.Cell(3, 4).Range.Text = format_score(county_avg.get("prog_nei", 30.0) + county_avg.get("prog_wai", 20.0))
        t.Cell(4, 4).Range.Text = format_score(county_avg.get("policy", 15.0))
        
        
        effect_score = county_avg.get("effect_nei", 10.0) + county_avg.get("effect_wai", 10.0)
        deduct_total = (0.5 if special1 else 0.0) + (1.0 if special2 else 0.0) + special3
        if deduct_total > 0:
            effect_score -= deduct_total
            rng = t.Cell(5, 5).Range
            find = rng.Find
            
            if special1:
                find.Text = '□对落实省市级验收方案要求不严格的'
                find.Replacement.Text = '☑对落实省市级验收方案要求不严格的'
                find.Execute(Replace=2)
                
            if special2:
                find.Text = '□对落实省市级验收方案要求走过场、未能反映真实情况的'
                find.Replacement.Text = '☑对落实省市级验收方案要求走过场、未能反映真实情况的'
                find.Execute(Replace=2)
                
            if special3 > 0:
                find.Text = '□对存在整组未延包的'
                find.Replacement.Text = '☑对存在整组未延包的'
                find.Execute(Replace=2)
                
                find.Text = '扣0.5-1分。'
                find.Replacement.Text = f'扣0.5-1分。（实际扣除：{special3}分）。'
                find.Execute(Replace=2)
 # wdReplaceAll
            
            rng = t.Cell(5, 5).Range
            find = rng.Find
            find.Text = '扣0.5-1分。'
            find.Replacement.Text = f'扣0.5-1分。（实际扣除：{special3}分）。'
            find.Execute(Replace=2)
            
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
        find.Text = '检查结果评定为'
        find.Execute()
        if find.Found:
            rng = find.Parent
            rng.End = rng.End + 6
            rng.Text = f'检查结果评定为 {check_level} '
            
        find = doc.Content.Find
        find.Text = '验收结果评定为'
        find.Execute()
        if find.Found:
            rng = find.Parent
            rng.End = rng.End + 6
            rng.Text = f'验收结果评定为 {accept_level} '
        
        doc.SaveAs2(FileName=out_path, FileFormat=0)
        doc.Close(0)
        doc = None
        word.Quit()
        word = None
        return "/api/download?file=downloads/附件11_全椒县县级自查验收评定表.doc"
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