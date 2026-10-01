import os
import re
import shutil
import pythoncom
import win32com.client
from collections import defaultdict
from database import get_base_dir


def _cell_replace_checkbox(cell, option, checked=True):
    """Replace a checkbox in a Word table cell while preserving paragraph structure.

    Each paragraph's Range.Text ends with chr(13) (para mark). We strip only chr(7)
    (cell terminator on the last para), do the substitution, then write the text
    back including the chr(13) so the paragraph mark is never destroyed.
    """
    mark = '☑' if checked else '□'
    cell_rng = cell.Range
    for i in range(1, cell_rng.Paragraphs.Count + 1):
        p = cell_rng.Paragraphs(i)
        raw = p.Range.Text          # includes trailing \r (and \x07 on last para)
        clean = raw.replace('\x07', '')  # remove cell terminator, keep \r
        if ('□' + option) not in clean:
            continue
        new_txt = clean.replace('□' + option, mark + option)
        p.Range.Text = new_txt      # \r is still there, para mark survives
        break

def _set_issues_cell(cell, issues):
    """Write numbered issues separated by semicolons on a single line."""
    rng = cell.Range
    rng.MoveEnd(1, -1)
    if issues:
        parts = [f'{idx+1}.{str(v)}' for idx, v in enumerate(issues)]
        rng.Text = '；'.join(parts)
    else:
        rng.Text = '无'






def _insert_sign_img(doc, names, sign_data):
    if not sign_data: return
    
    import uuid, base64, os
    abs_path = None
    if sign_data.startswith("data:image"):
        head, b64_str = sign_data.split(',', 1)
        img_data = base64.b64decode(b64_str)
        tmp_path = os.path.abspath(f"uploads/signatures/tmp_{uuid.uuid4().hex}.png")
        os.makedirs("uploads/signatures", exist_ok=True)
        with open(tmp_path, "wb") as f:
            f.write(img_data)
        abs_path = tmp_path
    elif "file=" in sign_data:
        rel_path = sign_data.split("file=")[1]
        abs_path = os.path.abspath(rel_path)
        
    if not abs_path or not os.path.exists(abs_path): return
    
    for name in names:
        if doc.Bookmarks.Exists(name):
            rng = doc.Bookmarks(name).Range
            rng.Text = ""
            shape = rng.InlineShapes.AddPicture(FileName=abs_path, LinkToFile=False, SaveWithDocument=True)
            ratio = shape.Width / shape.Height if shape.Height else 2
            shape.Height = 30
            shape.Width = 30 * ratio

from datetime import datetime

def replace_common_bookmarks(doc, county_name: str, date_str: str = None):
    """
    通用替换所有附件中的全局书签：
    1. county_name -> 县级区域名称
    2. date -> 当前时间 XXXX年XX月XX日
    """
    if not date_str:
        now = datetime.now()
        date_str = f"{now.year}年{now.month:02d}月{now.day:02d}日"

    if doc.Bookmarks.Exists("county_name"):
        try:
            doc.Bookmarks("county_name").Range.Text = county_name
        except Exception as e:
            print(f"替换书签 county_name 异常: {e}")

    if doc.Bookmarks.Exists("county_name1"):
        try:
            doc.Bookmarks("county_name1").Range.Text = county_name
        except Exception as e:
            print(f"替换书签 county_name1 异常: {e}")

    if doc.Bookmarks.Exists("date"):
        try:
            doc.Bookmarks("date").Range.Text = date_str
        except Exception as e:
            print(f"替换书签 date 异常: {e}")

def replace_att6_bookmarks(doc, county_name: str, date_str: str = None):
    """
    针对附件6各分表书签替换：
    county_name1/2/3/4 -> 县级区域名称
    date1/2/3/4 -> 当前时间 XXXX年XX月XX日
    """
    if not date_str:
        now = datetime.now()
        date_str = f"{now.year}年{now.month:02d}月{now.day:02d}日"

    for i in range(1, 5):
        bm_c = f"county_name{i}"
        if doc.Bookmarks.Exists(bm_c):
            try:
                doc.Bookmarks(bm_c).Range.Text = county_name
            except Exception as e:
                print(f"替换书签 {bm_c} 异常: {e}")

        bm_d = f"date{i}"
        if doc.Bookmarks.Exists(bm_d):
            try:
                doc.Bookmarks(bm_d).Range.Text = date_str
            except Exception as e:
                print(f"替换书签 {bm_d} 异常: {e}")

    # 全文自适应替换县级名称（支持明光市/全椒县等不同数据库上下文）
    if county_name:
        for old_c in ["全椒县", "明光市"]:
            if old_c != county_name:
                try:
                    rng = doc.Content
                    f = rng.Find
                    f.ClearFormatting()
                    f.Replacement.ClearFormatting()
                    f.Execute(FindText=old_c, ReplaceWith=county_name, Replace=2, MatchCase=True)
                except Exception as e:
                    print(f"全文自适应替换 {old_c} -> {county_name} 异常: {e}")

def _fill_bookmarks(doc, names, text):
    """Fill named bookmarks with text, padding with spaces to original length."""
    for name in names:
        if doc.Bookmarks.Exists(name):
            bm = doc.Bookmarks(name)
            bm_len = bm.End - bm.Start
            padded = (text + " " * bm_len)[:bm_len]
            bm_rng = bm.Range
            bm_rng.Text = padded
            # Re-add bookmark since .Text assignment removes it
            doc.Bookmarks.Add(name, bm_rng)

def sanitize_filename(name):
    clean = re.sub(r'[\\/*?:"<>|（）() ]', "", str(name or "")).strip()
    return clean if clean else "组"

def format_score(score):
    if score is None:
        return ""
    if isinstance(score, (int, float)):
        if score == int(score):
            return str(int(score))
        return f"{score:.1f}"
    return str(score)

def calculate_neiye_subscores(form_data):
    # 1. 机制运行 (满分15)
    d_m1 = 2.0 if form_data.get('mech_1') else 0.0
    d_m2 = 0.0
    for opt in form_data.get('mech_2', []):
        if '支付不规范' in opt: d_m2 += 4.0
        elif '支付不及时' in opt: d_m2 += 4.0
        elif '兜底' in opt: d_m2 += 2.0
    d_m2 = min(d_m2, 10.0)
    d_m3 = 2.0 if form_data.get('mech_3') else 0.0
    
    # 培训 (可为列表或count)
    if isinstance(form_data.get('mech_4'), list):
        d_m4 = min(len(form_data.get('mech_4', [])) * 0.5, 1.0)
    else:
        d_m4 = min(float(form_data.get('mech_4_count', 0) or 0) * 0.5, 1.0)
    
    deduct_mech = min(d_m1 + d_m2 + d_m3 + d_m4, 15.0)
    score_mech = max(15.0 - deduct_mech, 0.0)
    
    # 2. 程序规范 (满分30)
    d_p1 = 5.0 if form_data.get('prog_1') else 0.0
    d_p2 = min(len(form_data.get('prog_2', [])) * 0.5, 5.0)
    d_p3 = 5.0 if form_data.get('prog_3') else 0.0
    
    p4_list = form_data.get('prog_4', [])
    if any('没有公示材料' in x or '不足15天' in x for x in p4_list):
        d_p4 = 2.0
    else:
        d_p4 = min(len(p4_list) * 0.5, 2.0)
        
    d_p5 = 3.0 if form_data.get('prog_5') else 0.0
    
    p6_list = form_data.get('prog_6', [])
    if any(x in p6_list for x in ['未进行信息共享', '未与不动产登记部门有序衔接', '承包地块间重叠', '承包地块与宅基地重叠', '承包地块与其它自然资源部门要求的要素重叠']):
        d_p6 = 5.0
    else:
        d_p6 = min(len(p6_list) * 0.5, 5.0)

    p7_list = form_data.get('prog_7', [])
    if any(x in p7_list for x in ['档案整理第三方无涉密档案整理资质', '没有进行档案验收', '档案验收不符合相关标准']):
        d_p7 = 5.0
    else:
        d_p7 = min(len(p7_list) * 1.0, 5.0)
    
    deduct_prog = min(d_p1 + d_p2 + d_p3 + d_p4 + d_p5 + d_p6 + d_p7, 30.0)
    score_prog = max(30.0 - deduct_prog, 0.0)
    
    # 3. 政策落实 (满分15)
    d_pol1 = min(len(form_data.get('policy_1', [])) * 1.0, 3.0)
    c_2_1 = float(form_data.get('policy_2_1', 0) or 0)
    c_2_2 = float(form_data.get('policy_2_2', 0) or 0)
    c_2_3 = float(form_data.get('policy_2_3', 0) or 0)
    d_pol2 = min((c_2_1 + c_2_2 + c_2_3) * 1.0, 3.0)
    
    c_3_1 = float(form_data.get('policy_3_1', 0) or 0)
    c_3_2 = float(form_data.get('policy_3_2', 0) or 0)
    c_3_3 = float(form_data.get('policy_3_3', 0) or 0)
    c_3_4 = float(form_data.get('policy_3_4', 0) or 0)
    c_3_5 = float(form_data.get('policy_3_5', 0) or 0)
    d_pol3 = min((c_3_1 + c_3_2 + c_3_3 + c_3_4 + c_3_5) * 1.0, 3.0)
    
    d_pol4 = min(len(form_data.get('policy_4', [])) * 0.5, 3.0)
    d_pol5 = min(len(form_data.get('policy_5', [])) * 0.5, 3.0)
    
    deduct_policy = min(d_pol1 + d_pol2 + d_pol3 + d_pol4 + d_pol5, 15.0)
    score_policy = max(15.0 - deduct_policy, 0.0)
    
    # 4. 工作成效 (满分10)
    deduct_effect = min(len(form_data.get('effect_1', [])) * 1.0, 10.0)
    score_effect = max(10.0 - deduct_effect, 0.0)
    
    total_score = score_mech + score_prog + score_policy + score_effect
    
    return {
        "deduct": {
            "m1": d_m1, "m2": d_m2, "m3": d_m3, "m4": d_m4, "mech": deduct_mech,
            "p1": d_p1, "p2": d_p2, "p3": d_p3, "p4": d_p4, "p5": d_p5, "p6": d_p6, "p7": d_p7, "prog": deduct_prog,
            "pol1": d_pol1, "pol2": d_pol2, "pol3": d_pol3, "pol4": d_pol4, "pol5": d_pol5, "policy": deduct_policy,
            "effect": deduct_effect
        },
        "score": {
            "mech": score_mech,
            "prog": score_prog,
            "policy": score_policy,
            "effect": score_effect,
            "total": total_score
        }
    }

def fill_table_1(t1, form_data, scores):
    # R2: 配套延包
    items_1 = [x for x in form_data.get("mech_1", []) if x]
    t1.Rows(2).Cells(4).Range.Text = "\n".join(items_1) if items_1 else "无"
    t1.Rows(2).Cells(5).Range.Text = "/"
    t1.Rows(2).Cells(6).Range.Text = f"{scores['deduct']['m1']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['m1'] > 0 else "0"
    
    # R3: 经费保障
    items_2 = [x for x in form_data.get("mech_2", []) if x]
    t1.Rows(3).Cells(4).Range.Text = "\n".join(items_2) if items_2 else "无"
    t1.Rows(3).Cells(5).Range.Text = "/"
    t1.Rows(3).Cells(6).Range.Text = f"{scores['deduct']['m2']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['m2'] > 0 else "0"

    # R4: 宣传
    items_3 = [x for x in form_data.get("mech_3", []) if x]
    t1.Rows(4).Cells(4).Range.Text = "\n".join(items_3) if items_3 else "无"
    t1.Rows(4).Cells(5).Range.Text = "/"
    t1.Rows(4).Cells(6).Range.Text = f"{scores['deduct']['m3']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['m3'] > 0 else "0"

    # R5: 培训
    items_4 = [x for x in form_data.get("mech_4", []) if x]
    t1.Rows(5).Cells(4).Range.Text = "\n".join(items_4) if items_4 else "无"
    t1.Rows(5).Cells(5).Range.Text = "/"
    t1.Rows(5).Cells(6).Range.Text = f"{scores['deduct']['m4']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['m4'] > 0 else "0"

    # R6: 总计扣分
    t1.Rows(6).Cells(3).Range.Text = f"{scores['deduct']['mech']:.1f}".rstrip('0').rstrip('.')
    
    # R7: 重要问题描述
    issues = []
    if items_1: issues.extend(items_1)
    if items_2: issues.extend(items_2)
    if items_3: issues.extend(items_3)
    if items_4: issues.extend(items_4)
    _set_issues_cell(t1.Rows(7).Cells(2), issues) 

def fill_table_2(t2, form_data, scores):
    # R2: 成立机构
    items_1 = [x for x in form_data.get("prog_1", []) if x]
    t2.Rows(2).Cells(4).Range.Text = "\n".join(items_1) if items_1 else "无"
    t2.Rows(2).Cells(5).Range.Text = "/"
    t2.Rows(2).Cells(6).Range.Text = f"{scores['deduct']['p1']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p1'] > 0 else "0"

    # R3: 摸底核实
    items_2 = [x for x in form_data.get("prog_2", []) if x]
    t2.Rows(3).Cells(4).Range.Text = "\n".join(items_2) if items_2 else "无"
    t2.Rows(3).Cells(5).Range.Text = "/"
    t2.Rows(3).Cells(6).Range.Text = f"{scores['deduct']['p2']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p2'] > 0 else "0"

    # R4: 制定方案
    items_3 = [x for x in form_data.get("prog_3", []) if x]
    t2.Rows(4).Cells(4).Range.Text = "\n".join(items_3) if items_3 else "无"
    t2.Rows(4).Cells(5).Range.Text = "/"
    t2.Rows(4).Cells(6).Range.Text = f"{scores['deduct']['p3']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p3'] > 0 else "0"

    # R5: 调查公示
    items_4 = [x for x in form_data.get("prog_4", []) if x]
    t2.Rows(5).Cells(4).Range.Text = "\n".join(items_4) if items_4 else "无"
    t2.Rows(5).Cells(5).Range.Text = "/"
    t2.Rows(5).Cells(6).Range.Text = f"{scores['deduct']['p4']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p4'] > 0 else "0"

    # R6: 签订合同
    items_5 = [x for x in form_data.get("prog_5", []) if x]
    t2.Rows(6).Cells(4).Range.Text = "\n".join(items_5) if items_5 else "无"
    t2.Rows(6).Cells(5).Range.Text = "/"
    t2.Rows(6).Cells(6).Range.Text = f"{scores['deduct']['p5']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p5'] > 0 else "0"

    # R7: 完善证书
    items_6 = [x for x in form_data.get("prog_6", []) if x]
    t2.Rows(7).Cells(4).Range.Text = "\n".join(items_6) if items_6 else "无"
    t2.Rows(7).Cells(5).Range.Text = "/"
    t2.Rows(7).Cells(6).Range.Text = f"{scores['deduct']['p6']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p6'] > 0 else "0"

    # R8: 资料归档
    items_7 = [x for x in form_data.get("prog_7", []) if x]
    t2.Rows(8).Cells(4).Range.Text = "\n".join(items_7) if items_7 else "无"
    t2.Rows(8).Cells(5).Range.Text = "/"
    t2.Rows(8).Cells(6).Range.Text = f"{scores['deduct']['p7']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p7'] > 0 else "0"

    # R9: 总计扣分
    t2.Rows(9).Cells(3).Range.Text = f"{scores['deduct']['prog']:.1f}".rstrip('0').rstrip('.')
    
    # R10: 重要问题描述
    issues = []
    if items_1: issues.extend(items_1)
    if items_2: issues.extend(items_2)
    if items_3: issues.extend(items_3)
    if items_4: issues.extend(items_4)
    if items_5: issues.extend(items_5)
    if items_6: issues.extend(items_6)
    if items_7: issues.extend(items_7)
    _set_issues_cell(t2.Rows(10).Cells(2), issues) 

def fill_table_3(t3, form_data, scores):
    # R2: 大稳定、小调整
    items_1 = [x for x in form_data.get("policy_1", []) if x]
    t3.Rows(2).Cells(4).Range.Text = "\n".join(items_1) if items_1 else "无"
    t3.Rows(2).Cells(5).Range.Text = "/"
    t3.Rows(2).Cells(6).Range.Text = f"{scores['deduct']['pol1']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol1'] > 0 else "0"

    # R3: 保障土地承包权益 (带数量)
    items_2 = []
    c_2_1 = int(form_data.get("policy_2_1", 0) or 0)
    c_2_2 = int(form_data.get("policy_2_2", 0) or 0)
    c_2_3 = int(form_data.get("policy_2_3", 0) or 0)
    if c_2_1 > 0: items_2.append(f"未保障特殊群体权益（{c_2_1}起）")
    if c_2_2 > 0: items_2.append(f"未保障无地户权益（{c_2_2}起）")
    if c_2_3 > 0: items_2.append(f"没有统计（关注）特殊群体（{c_2_3}起）")
    t3.Rows(3).Cells(4).Range.Text = "\n".join(items_2) if items_2 else "无"
    t3.Rows(3).Cells(5).Range.Text = "/"
    t3.Rows(3).Cells(6).Range.Text = f"{scores['deduct']['pol2']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol2'] > 0 else "0"

    # R4: 依法收回消亡户承包地 (带数量)
    items_3 = []
    c_3_1 = int(form_data.get("policy_3_1", 0) or 0)
    c_3_2 = int(form_data.get("policy_3_2", 0) or 0)
    c_3_3 = int(form_data.get("policy_3_3", 0) or 0)
    c_3_4 = int(form_data.get("policy_3_4", 0) or 0)
    c_3_5 = int(form_data.get("policy_3_5", 0) or 0)
    if c_3_1 > 0: items_3.append(f"没有应收尽收（{c_3_1}起）")
    if c_3_2 > 0: items_3.append(f"采用不正当方式隐匿消亡户（{c_3_2}起）")
    if c_3_3 > 0: items_3.append(f"违规处置消亡土地（{c_3_3}起）")
    if c_3_4 > 0: items_3.append(f"没有统计消亡户（{c_3_4}起）")
    if c_3_5 > 0: items_3.append(f"没有分清实际消亡户和伪消亡户（{c_3_5}起）")
    t3.Rows(4).Cells(4).Range.Text = "\n".join(items_3) if items_3 else "无"
    t3.Rows(4).Cells(5).Range.Text = "/"
    t3.Rows(4).Cells(6).Range.Text = f"{scores['deduct']['pol3']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol3'] > 0 else "0"

    # R5: 严格机动地和新增耕地管理
    items_4 = [x for x in form_data.get("policy_4", []) if x]
    t3.Rows(5).Cells(4).Range.Text = "\n".join(items_4) if items_4 else "无"
    t3.Rows(5).Cells(5).Range.Text = "/"
    t3.Rows(5).Cells(6).Range.Text = f"{scores['deduct']['pol4']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol4'] > 0 else "0"

    # R6: 从严掌握确权确股不确地
    items_5 = [x for x in form_data.get("policy_5", []) if x]
    t3.Rows(6).Cells(4).Range.Text = "\n".join(items_5) if items_5 else "无"
    t3.Rows(6).Cells(5).Range.Text = "/"
    t3.Rows(6).Cells(6).Range.Text = f"{scores['deduct']['pol5']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol5'] > 0 else "0"

    # R7: 总计扣分
    t3.Rows(7).Cells(3).Range.Text = f"{scores['deduct']['policy']:.1f}".rstrip('0').rstrip('.')
    
    # R8: 重要问题描述
    issues = []
    if items_1: issues.extend(items_1)
    if items_2: issues.extend(items_2)
    if items_3: issues.extend(items_3)
    if items_4: issues.extend(items_4)
    if items_5: issues.extend(items_5)
    _set_issues_cell(t3.Rows(8).Cells(2), issues) 

def fill_table_4(t4, form_data, scores):
    # R2: 加强风险防范
    items_1 = [x for x in form_data.get("effect_1", []) if x]
    t4.Rows(2).Cells(4).Range.Text = "\n".join(items_1) if items_1 else "无"
    t4.Rows(2).Cells(5).Range.Text = "/"
    t4.Rows(2).Cells(6).Range.Text = f"{scores['deduct']['effect']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['effect'] > 0 else "0"

    # R3: 总计扣分
    t4.Rows(3).Cells(3).Range.Text = f"{scores['deduct']['effect']:.1f}".rstrip('0').rstrip('.')
    
    # R4: 重要问题描述
    issues = []
    if items_1: issues.extend(items_1)
    _set_issues_cell(t4.Rows(4).Cells(2), issues)

def export_neiye_att6_township(qsdwmc, form_data, township_name=None, village_name=None):
    pythoncom.CoInitialize()
    try:
        from database import get_county_and_townships_sync
        county_info, _ = get_county_and_townships_sync()
        county_name = county_info.get("name", "全椒县")

        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        
        base_dir = get_base_dir()
        tpl = os.path.join(base_dir, "附件", "附件6.doc")
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        clean_target = sanitize_filename(qsdwmc)
        out_filename = f"附件6_{county_name}县级自查内业组检查记录表_{clean_target}.doc"
        out_path = os.path.join(base_dir, "backend", "downloads", out_filename)
        shutil.copy(tpl, out_path)
        
        doc = word.Documents.Open(out_path)
        
        # 替换通用与附件6书签：county_name1/2/3/4 -> 县级区域名称，date1/2/3/4 -> 当前时间
        replace_common_bookmarks(doc, county_name)
        replace_att6_bookmarks(doc, county_name)

        # 映射 xzqh_1 ~ xzqh_4 书签：
        # - 若为乡镇级（无村名或村名为镇名），映射为 XX县XX镇
        # - 若为村级，映射为 XX县XX镇XX村
        t_part = township_name or ""
        v_part = village_name or ""
        if not t_part and not v_part:
            # 尝试从 qsdwmc 解析 (例如 "明光街道 - 蔬菜村" 或 "襄河镇")
            if " - " in qsdwmc:
                parts = qsdwmc.split(" - ", 1)
                t_part, v_part = parts[0].strip(), parts[1].strip()
            else:
                t_part = qsdwmc.strip()
                v_part = ""

        # 如果村名与镇名相同或村名为空，判定为乡镇级
        if v_part == t_part:
            v_part = ""

        # 规整县、镇、村文本，防止出现重复前缀（如 明光市明光街道蔬菜村）
        if t_part:
            if t_part.startswith(county_name):
                base_tv = t_part
            else:
                base_tv = f"{county_name}{t_part}"
        else:
            base_tv = county_name

        if v_part:
            if v_part.startswith(base_tv):
                _xzqh_text = v_part
            elif t_part and v_part.startswith(t_part):
                _xzqh_text = f"{county_name}{v_part}" if not v_part.startswith(county_name) else v_part
            else:
                _xzqh_text = f"{base_tv}{v_part}"
        else:
            # 严格满足要求：乡镇级映射为 XX县XX镇
            _xzqh_text = base_tv

        _fill_bookmarks(doc, ["xzqh_1", "xzqh_2", "xzqh_3", "xzqh_4", "xzqh1", "xzqh2", "xzqh3", "xzqh4"], _xzqh_text)
        jcz_sign = form_data.get("jcz_sign")
        fhz_sign = form_data.get("fhz_sign")
        _fill_bookmarks(doc, ["jcz1", "jcz2", "jcz3", "jcz4"], form_data.get("jcz_name") or "")
        _fill_bookmarks(doc, ["fhz1", "fhz2", "fhz3", "fhz4"], form_data.get("fhz_name") or "")
        
        scores = calculate_neiye_subscores(form_data)
        
        fill_table_1(doc.Tables(1), form_data, scores)
        fill_table_2(doc.Tables(2), form_data, scores)
        fill_table_3(doc.Tables(3), form_data, scores)
        fill_table_4(doc.Tables(4), form_data, scores)
        
        doc.Save()
        doc.Close(False)
        word.Quit()
        return f"/api/download?file=downloads/{out_filename}"
    except Exception as e:
        print("export_neiye_att6_township error:", e)
        try: word.Quit()
        except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()

def export_neiye_att6_county(form_data):
    """县级自查：导出机制运行 1/4 与工作成效 4/4"""
    return export_neiye_att6_mech_and_effect(form_data, is_county=True)

def export_neiye_att6_mechanism_only(form_data, is_county=False, township_name=None):
    """兼容旧接口名称：导出机制运行 1/4 与工作成效 4/4"""
    return export_neiye_att6_mech_and_effect(form_data, is_county=is_county, township_name=township_name)

def export_neiye_att6_mech_and_effect(form_data, is_county=False, township_name=None):
    """
    导出包含【机制运行 (1/4)】与【工作成效 (4/4)】的附件6检查记录表：
    - is_county=True 时：适用于县级自查，xzqh 书签映射为 XX县，输出 附件6_{county_name}县级自查内业组检查记录表（1_4、4_4）.doc
    - is_county=False 时：适用于乡镇级自查，xzqh 书签映射为 XX县XX镇，输出 附件6_{county_name}县级自查内业组检查记录表_{clean_ts}（1_4、4_4）.doc
    - 自动填充 Table 1 机制运行与 Table 4 工作成效
    - 物理删除第 2/4 (程序规范) 和第 3/4 (政策落实)，保留第 1/4 和第 4/4 完整版式并保存
    """
    pythoncom.CoInitialize()
    try:
        from database import get_county_and_townships_sync
        county_info, _ = get_county_and_townships_sync()
        county_name = county_info.get("name", "全椒县")

        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        
        base_dir = get_base_dir()
        tpl = os.path.join(base_dir, "附件", "附件6.doc")
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        
        if is_county or not township_name:
            out_filename = f"附件6_{county_name}县级自查内业组检查记录表（1_4、4_4）.doc"
            xzqh_text = county_name
        else:
            clean_ts = sanitize_filename(township_name)
            out_filename = f"附件6_{county_name}县级自查内业组检查记录表_{clean_ts}（1_4、4_4）.doc"
            if clean_ts.startswith(county_name):
                xzqh_text = clean_ts
            else:
                xzqh_text = f"{county_name}{clean_ts}"

        out_path = os.path.join(base_dir, "backend", "downloads", out_filename)
        shutil.copy(tpl, out_path)
        
        doc = word.Documents.Open(out_path)
        
        # 替换通用与附件6书签：county_name1/2/3/4 -> 县级区域名称，date1/2/3/4 -> 当前时间
        replace_common_bookmarks(doc, county_name)
        replace_att6_bookmarks(doc, county_name)

        # 填充第 1/4 与第 4/4 页的行政区划与人员书签
        _fill_bookmarks(doc, ["xzqh_1", "xzqh1", "xzqh_4", "xzqh4"], xzqh_text)
        _fill_bookmarks(doc, ["jcz1", "jcz4"], form_data.get("jcz_name") or "")
        _fill_bookmarks(doc, ["fhz1", "fhz4"], form_data.get("fhz_name") or "")
        
        scores = calculate_neiye_subscores(form_data)
        fill_table_1(doc.Tables(1), form_data, scores)
        fill_table_4(doc.Tables(4), form_data, scores)
        
        # 删除第 2/4 (程序规范) 和第 3/4 (政策落实)
        sec2_start = None
        sec4_start = None
        for p in doc.Paragraphs:
            t = p.Range.Text
            if "（2/4）" in t:
                sec2_start = p.Range.Start
            elif "（4/4）" in t:
                sec4_start = p.Range.Start
        if sec2_start and sec4_start:
            doc.Range(sec2_start, sec4_start).Delete()
        
        doc.Save()
        doc.Close(False)
        word.Quit()
        return f"/api/download?file=downloads/{out_filename}"
    except Exception as e:
        print("export_neiye_att6_mech_and_effect error:", e)
        try: word.Quit()
        except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()

def export_neiye_att7(records_by_qsdwdm, township_villages_map=None):
    pythoncom.CoInitialize()
    try:
        from database import get_county_and_townships_sync
        county_info, township_list_raw = get_county_and_townships_sync()
        county_code = county_info.get("code", "341124")
        county_name = county_info.get("name", "全椒县")

        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        
        base_dir = get_base_dir()
        tpl = os.path.join(base_dir, "附件", "附件7.doc")
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_filename = f"附件7_{county_name}县级自查内业组检查得分表.doc"
        out_path = os.path.join(base_dir, "backend", "downloads", out_filename)
        shutil.copy(tpl, out_path)
        
        doc = word.Documents.Open(out_path)
        replace_common_bookmarks(doc, county_name)
        t = doc.Tables(1)
        
        # 1. 县级行 (Row 2) - 机制运行(15分) + 工作成效(10分)
        county_rec = records_by_qsdwdm.get(county_code) or records_by_qsdwdm.get("341124")
        if county_rec:
            c_scores = calculate_neiye_subscores(county_rec.get("form_data", {}))
            county_mech = c_scores['score']['mech']
            county_effect = c_scores['score']['effect']
        else:
            county_mech = 15.0
            county_effect = 10.0

        t.Rows(2).Cells(1).Range.Text = "1"
        t.Rows(2).Cells(2).Range.Text = county_name
        t.Rows(2).Cells(3).Range.Text = f"{county_mech:.1f}".rstrip('0').rstrip('.')
        t.Rows(2).Cells(4).Range.Text = "/"
        t.Rows(2).Cells(5).Range.Text = "/"
        t.Rows(2).Cells(6).Range.Text = f"{county_effect:.1f}".rstrip('0').rstrip('.')
        t.Rows(2).Cells(7).Range.Text = f"{(county_mech + county_effect):.1f}".rstrip('0').rstrip('.')

        township_list = [(t["code"], t["name"]) for t in township_list_raw]
        N = len(township_list)
        # 表格初始结构：Row 1 表头，Row 2 县级行，最后一行是总评行
        current_reserved_ts_rows = t.Rows.Count - 3
        if N > current_reserved_ts_rows:
            for _ in range(N - current_reserved_ts_rows):
                t.Rows.Add(t.Rows(t.Rows.Count))
        elif N < current_reserved_ts_rows:
            for _ in range(current_reserved_ts_rows - N):
                t.Rows(t.Rows.Count - 1).Delete()
        
        sums = {"mech": 0.0, "prog": 0.0, "policy": 0.0, "effect": 0.0, "total": 0.0}
        count_evaluated = 0
        
        # 如果未传入乡镇与抽样村对应关系，尝试构建映射
        ts_v_map = township_villages_map or {}
        
        for idx, (code, name) in enumerate(township_list):
            r_idx = idx + 3
            t.Rows(r_idx).Cells(1).Range.Text = str(idx + 2)
            t.Rows(r_idx).Cells(2).Range.Text = name
            
            # 获取该乡镇本级的机制运行与工作成效得分 (qsdwdm == code 或 level == 'township')
            township_rec = records_by_qsdwdm.get(code)
            township_self_mech = None
            township_self_effect = None
            if township_rec:
                ts_scores = calculate_neiye_subscores(township_rec.get("form_data", {}))["score"]
                township_self_mech = ts_scores["mech"]
                township_self_effect = ts_scores["effect"]

            # 获取该乡镇下所有抽样村在 neiye_records 中的记录
            v_codes = ts_v_map.get(name, [])
            village_recs = []
            if v_codes:
                for vc in v_codes:
                    if vc in records_by_qsdwdm:
                        village_recs.append(records_by_qsdwdm[vc])
            else:
                for r_code, r_data in records_by_qsdwdm.items():
                    if r_code != county_code and (r_code == code or (r_code.startswith(code) and len(r_code) > 9)):
                        village_recs.append(r_data)
            
            if village_recs or township_self_mech is not None or township_self_effect is not None:
                count_evaluated += 1
                v_scores = [calculate_neiye_subscores(vr.get("form_data", {}))["score"] for vr in village_recs]
                k = len(v_scores)
                
                # 计算下属抽样村各项指标平均分
                if k > 0:
                    village_avg_mech = sum(s["mech"] for s in v_scores) / k
                    sc_prog = sum(s["prog"] for s in v_scores) / k
                    sc_policy = sum(s["policy"] for s in v_scores) / k
                    village_avg_effect = sum(s["effect"] for s in v_scores) / k
                else:
                    village_avg_mech = None
                    sc_prog = 0.0
                    sc_policy = 0.0
                    village_avg_effect = None

                # 机制运行得分计算方式：该乡镇机制运行得分与乡镇下属村的机制运行平均分
                if township_self_mech is not None and village_avg_mech is not None:
                    sc_mech = (township_self_mech + village_avg_mech) / 2.0
                elif township_self_mech is not None:
                    sc_mech = township_self_mech
                elif village_avg_mech is not None:
                    sc_mech = village_avg_mech
                else:
                    sc_mech = 15.0

                # 工作成效得分计算方式：该乡镇工作成效得分与乡镇下属村的工作成效平均分
                if township_self_effect is not None and village_avg_effect is not None:
                    sc_effect = (township_self_effect + village_avg_effect) / 2.0
                elif township_self_effect is not None:
                    sc_effect = township_self_effect
                elif village_avg_effect is not None:
                    sc_effect = village_avg_effect
                else:
                    sc_effect = 10.0

                sc_total = sc_mech + sc_prog + sc_policy + sc_effect

                t.Rows(r_idx).Cells(3).Range.Text = f"{sc_mech:.1f}".rstrip('0').rstrip('.')
                t.Rows(r_idx).Cells(4).Range.Text = f"{sc_prog:.1f}".rstrip('0').rstrip('.') if k > 0 else "/"
                t.Rows(r_idx).Cells(5).Range.Text = f"{sc_policy:.1f}".rstrip('0').rstrip('.') if k > 0 else "/"
                t.Rows(r_idx).Cells(6).Range.Text = f"{sc_effect:.1f}".rstrip('0').rstrip('.')
                t.Rows(r_idx).Cells(7).Range.Text = f"{sc_total:.1f}".rstrip('0').rstrip('.')
                
                sums["mech"] += sc_mech
                sums["prog"] += sc_prog
                sums["policy"] += sc_policy
                sums["effect"] += sc_effect
                sums["total"] += sc_total
            else:
                t.Rows(r_idx).Cells(3).Range.Text = ""
                t.Rows(r_idx).Cells(4).Range.Text = ""
                t.Rows(r_idx).Cells(5).Range.Text = ""
                t.Rows(r_idx).Cells(6).Range.Text = ""
                t.Rows(r_idx).Cells(7).Range.Text = ""

        # Last Row: 总评 (平均分)
        summary_row = t.Rows.Count
        t.Rows(summary_row).Cells(1).Range.Text = str(N + 2)
        t.Rows(summary_row).Cells(2).Range.Text = "总评"
        if count_evaluated > 0:
            eval_count = count_evaluated + 1 # 乡镇 + 县级
            avg_mech = (sums['mech'] + county_mech) / eval_count
            avg_prog = sums['prog'] / count_evaluated
            avg_policy = sums['policy'] / count_evaluated
            avg_effect = (sums['effect'] + county_effect) / eval_count
            avg_total = avg_mech + avg_prog + avg_policy + avg_effect
            
            t.Rows(summary_row).Cells(3).Range.Text = f"{avg_mech:.1f}"
            t.Rows(summary_row).Cells(4).Range.Text = f"{avg_prog:.1f}"
            t.Rows(summary_row).Cells(5).Range.Text = f"{avg_policy:.1f}"
            t.Rows(summary_row).Cells(6).Range.Text = f"{avg_effect:.1f}"
            t.Rows(summary_row).Cells(7).Range.Text = f"{avg_total:.1f}"
        else:
            t.Rows(summary_row).Cells(3).Range.Text = ""
            t.Rows(summary_row).Cells(4).Range.Text = ""
            t.Rows(summary_row).Cells(5).Range.Text = ""
            t.Rows(summary_row).Cells(6).Range.Text = ""
            t.Rows(summary_row).Cells(7).Range.Text = ""

        doc.Save()
        doc.Close(False)
        word.Quit()
        return f"/api/download?file=downloads/{out_filename}"
    except Exception as e:
        print("export_neiye_att7 error:", e)
        try: word.Quit()
        except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()
def export_att4(township_name, farmer_count, total_area):
    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32com.client.DispatchEx('Word.Application')
        word.Visible = False
        word.DisplayAlerts = 0
        
        base_dir = get_base_dir()
        os.makedirs(os.path.join(base_dir, 'backend', 'downloads'), exist_ok=True)
        template = os.path.join(base_dir, '附件', '附件4.doc')
        clean_ts = sanitize_filename(township_name)
        out = os.path.join(base_dir, 'backend', 'downloads', f'附件4_成果检查验收申请表_{clean_ts}.doc')
        if os.path.exists(out):
            try: os.remove(out)
            except: pass
        shutil.copy(template, out)
        
        from database import get_county_and_townships_sync
        county_info, _ = get_county_and_townships_sync()
        county_name = county_info.get("name", "全椒县")

        doc = word.Documents.Open(FileName=out, ReadOnly=False, ConfirmConversions=False)
        replace_common_bookmarks(doc, county_name)
        t = doc.Tables(1)
        t.Cell(1, 2).Range.Text = township_name
        t.Cell(5, 2).Range.Text = str(farmer_count)
        t.Cell(6, 2).Range.Text = f"{total_area:.2f}"
        
        doc.SaveAs2(FileName=out, FileFormat=0)
        doc.Close(0)
        doc = None
        word.Quit()
        word = None
        return f"/api/download?file=downloads/附件4_成果检查验收申请表_{clean_ts}.doc"
    except Exception as e:
        print("Export att4 error:", e)
        if doc:
            try: doc.Close(0)
            except: pass
        if word:
            try: word.Quit()
            except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()

def export_att5(stats_data, township_code, township_name):
    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx('Word.Application')
        word.Visible = False
        word.DisplayAlerts = 0
        
        base_dir = get_base_dir()
        os.makedirs(os.path.join(base_dir, 'backend', 'downloads'), exist_ok=True)
        
        att5_template = os.path.join(base_dir, '附件', '附件5.doc')
        clean_ts = sanitize_filename(township_name)
        att5_out = os.path.join(base_dir, 'backend', 'downloads', f'附件5_抽样统计表_{clean_ts}.doc')
        if os.path.exists(att5_out):
            try: os.remove(att5_out)
            except: pass
        shutil.copy(att5_template, att5_out)
        
        doc5 = word.Documents.Open(FileName=att5_out, ReadOnly=False, ConfirmConversions=False)
        from database import get_county_and_townships_sync
        county_info, _ = get_county_and_townships_sync()
        county_name = county_info.get("name", "全椒县")
        replace_common_bookmarks(doc5, county_name)
        t5 = doc5.Tables(1)
        
        N = len(stats_data)
        while t5.Rows.Count > 2:
            t5.Rows(3).Delete()
            
        if N > 1:
            t5.Rows(2).Select()
            word.Selection.InsertRowsBelow(N - 1)
            
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
        word.ScreenUpdating = False
        
        base_dir = get_base_dir()
        tpl = os.path.join(base_dir, '附件', '附件8.doc')
        clean_ts = sanitize_filename(township_name)
        clean_vn = sanitize_filename(village_name)
        clean_gn = sanitize_filename(group_name)
        
        os.makedirs(os.path.join(base_dir, 'backend', 'downloads'), exist_ok=True)
        out_filename = f'附件8_外业核查记录表_{clean_ts}{clean_vn}{clean_gn}.doc'
        out_path = os.path.join(base_dir, 'backend', 'downloads', out_filename)
        if os.path.exists(out_path):
            try:
                os.remove(out_path)
            except Exception:
                # 若文件被占用，生成安全防冲突文件名
                out_filename = f'附件8_外业核查记录表_{clean_ts}{clean_vn}{clean_gn}_{uuid.uuid4().hex[:6]}.doc'
                out_path = os.path.join(base_dir, 'backend', 'downloads', out_filename)
        shutil.copy(tpl, out_path)
        
        doc8 = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
        from database import get_county_and_townships_sync
        county_info, _ = get_county_and_townships_sync()
        county_name = county_info.get("name", "全椒县")
        replace_common_bookmarks(doc8, county_name)

        now = datetime.now()
        date_str = f"{now.year} 年  {now.month:02d}  月  {now.day:02d}  日"
        p3 = doc8.Paragraphs(3)
        rng = p3.Range
        rng.End = rng.End - 1
        rng.Text = f"   乡镇：{township_name} \t行政村：{village_name} \t村民小组：{group_name}" + " "*25 + date_str
        
        t8 = doc8.Tables(1)
        for _ in range(5):
            try: t8.Rows(3).Delete()
            except: pass
            
        N_rows = len(group_rows)
        if N_rows > 1:
            t8.Rows(2).Select()
            word.Selection.InsertRowsBelow(N_rows - 1)
            
        total_errors = 0
        satisfaction_count = 0
        
        # Group by contractor to calculate unique contractor-level errors and satisfaction
        processed_contractors = set()
        contractor_count = 0

        for i, r in enumerate(group_rows):
            r_idx = i + 2
            farmer_name = r.get('cbfmc', '') or r.get('承包方代表', '')
            cbfbm = str(r.get("cbfbm", "") or r.get("cbfbm_short", "") or r.get("cbfmc", ""))
            is_first_parcel_of_cbf = (cbfbm not in processed_contractors)
            
            # Parcel-level errors
            for k in ['area_acknowledged', 'bound_correct', 'self_verified']:
                if r.get(k) == 'X':
                    total_errors += 1
            
            lxdh_val = str(r.get('lxdh', '') or r.get('联系电话', '') or '').strip()
            if lxdh_val == 'None':
                lxdh_val = ''
            is_phone_err = (str(r.get('phone_correct', '')).strip() == 'X')

            # Contractor-level errors & satisfaction
            sat = r.get('satisfaction', '满意')
            if is_first_parcel_of_cbf:
                processed_contractors.add(cbfbm)
                contractor_count += 1
                for k in ['rights_correct', 'member_qualified', 'self_signed']:
                    if r.get(k) == 'X':
                        total_errors += 1
                if is_phone_err:
                    total_errors += 1
                if sat == '满意':
                    satisfaction_count += 1

            # 序号、地块信息每行必填
            t8.Cell(r_idx, 1).Range.Text = str(i + 1)
            t8.Cell(r_idx, 5).Range.Text = str(r.get('dkmc', '') or r.get('地块名称', ''))
            t8.Cell(r_idx, 6).Range.Text = str(r.get('dkbm_short', '') or r.get('地块简编码', ''))
            t8.Cell(r_idx, 7).Range.Text = str(r.get('scmj', '') or r.get('成果面积(亩)', ''))

            # 地块级核查指标
            for c_pos, k_name in [(8, 'area_acknowledged'), (10, 'bound_correct'), (12, 'self_verified')]:
                cell_k = t8.Cell(r_idx, c_pos)
                val_k = r.get(k_name, '')
                if val_k == 'X':
                    cell_k.Range.Text = 'X'
                    cell_k.Range.Font.Color = 255
                else:
                    cell_k.Range.Text = '√'

            # 农户级指标（仅首行填值并设颜色，后续行保持空值，便于后续单元格纵向合并且不重复文字）
            if is_first_parcel_of_cbf:
                t8.Cell(r_idx, 2).Range.Text = farmer_name
                t8.Cell(r_idx, 3).Range.Text = str(r.get('cbfbm_short', '') or r.get('承包方编码(缩略码)', ''))
                
                cell_dh = t8.Cell(r_idx, 4)
                if is_phone_err:
                    cell_dh.Range.Text = 'X'
                    cell_dh.Range.Font.Color = 255
                else:
                    cell_dh.Range.Text = lxdh_val if lxdh_val else '/'

                for c_pos, k_name in [(9, 'rights_correct'), (11, 'member_qualified'), (13, 'self_signed')]:
                    cell_k = t8.Cell(r_idx, c_pos)
                    val_k = r.get(k_name, '')
                    if val_k == 'X':
                        cell_k.Range.Text = 'X'
                        cell_k.Range.Font.Color = 255
                    else:
                        cell_k.Range.Text = '√'

                t8.Cell(r_idx, 14).Range.Text = sat
                t8.Cell(r_idx, 15).Range.Text = r.get('survey_method', r.get('调查抽样方式', '现场'))
                t8.Cell(r_idx, 16).Range.Text = ""

        # Fill stats rows BEFORE any vertical merges
        total_count = len(group_rows)
        prog_score = max(20.0 - total_errors * 0.5, 0.0)
        effect_score = (satisfaction_count / contractor_count * 10.0) if contractor_count > 0 else 10.0
        
        r_stat_idx = total_count + 2
        t8.Cell(r_stat_idx, 2).Range.Text = str(total_errors)
        t8.Cell(r_stat_idx, 3).Range.Text = str(satisfaction_count)
        
        r_score_idx = total_count + 3
        t8.Cell(r_score_idx, 1).Range.Text = f"发包方程序规范得分=20-发包方错误总和({total_errors})×0.5={prog_score:.1f}；发包方工作成效（满意度调查）得分=满意数({satisfaction_count})/抽检数({contractor_count})×10={effect_score:.1f}"

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
        
        # 保持 100% 完整原版合并逻辑：合并全部 9 个农户级列
        for cbfbm, r_start, r_end in reversed(segments):
            if r_start < r_end:
                for col_idx in [16, 15, 14, 13, 11, 9, 4, 3, 2]:
                    try:
                        t8.Cell(r_start, col_idx).Merge(t8.Cell(r_end, col_idx))
                    except Exception as me:
                        print(f"Merge err at rows {r_start}-{r_end} col {col_idx}: {me}")
                cell_target = t8.Cell(r_start, 16)
            else:
                cell_target = t8.Cell(r_start, 16)

            sig_path = os.path.join(sig_dir, f"{cbfbm}.png")
            if os.path.exists(sig_path):
                try:
                    cell_target.Range.Text = ""
                    pic = cell_target.Range.InlineShapes.AddPicture(
                        FileName=os.path.abspath(sig_path), LinkToFile=False, SaveWithDocument=True
                    )
                    pic.Width = 65
                    pic.Height = 26
                    cell_target.Range.ParagraphFormat.Alignment = 1
                    cell_target.VerticalAlignment = 1
                except Exception as pe:
                    print(f"Insert signature pic error (ignored): {pe}")
                    cell_target.Range.Text = ""
            else:
                cell_target.Range.Text = ""

        try:
            t8.Range.ParagraphFormat.Alignment = 1
        except:
            pass
        doc8.SaveAs2(FileName=out_path, FileFormat=0)
        doc8.Close(0)
        doc8 = None
        word.Quit()
        word = None
        return f"/api/download?file=downloads/{out_filename}"
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
        from database import get_county_and_townships_sync
        county_info, township_list_raw = get_county_and_townships_sync()
        county_name = county_info.get("name", "全椒县")
        all_townships = [item["name"] for item in township_list_raw]

        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        
        base_dir = get_base_dir()
        tpl = os.path.join(base_dir, "附件", "附件9.doc")
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_filename = f"附件9_{county_name}县级自查外业组检查得分表.doc"
        out_path = os.path.join(base_dir, "backend", "downloads", out_filename)
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        shutil.copy(tpl, out_path)
        
        doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
        replace_common_bookmarks(doc, county_name)
        t = doc.Tables(1)
        
        # 1. 计算每个组的得分，并按 乡镇 -> 行政村 -> 村民小组 组织层级
        groups_map = defaultdict(list)
        for r in samples_rows:
            key = (r.get("township_name", ""), r.get("village_name", ""), r.get("group_name", ""))
            if key[0]:
                groups_map[key].append(r)
            
        # 结构：hierarchy[t_name][v_name] = [ { "group": g_name, "prog_score": ..., "effect_score": ... }, ... ]
        hierarchy = defaultdict(lambda: defaultdict(list))
        
        for (t_name, v_name, g_name), g_rows in groups_map.items():
            total_errors = 0
            satisfaction_count = 0
            processed_cbfs = set()
            c_cnt = 0
            for r in g_rows:
                for k in ["area_acknowledged", "bound_correct", "self_verified"]:
                    if r.get(k) == "X":
                        total_errors += 1
                
                cbf_key = str(r.get("cbfbm") or r.get("cbfbm_short") or r.get("cbfmc") or "")
                if cbf_key not in processed_cbfs:
                    processed_cbfs.add(cbf_key)
                    c_cnt += 1
                    for k in ["rights_correct", "member_qualified", "self_signed"]:
                        if r.get(k) == "X":
                            total_errors += 1
                    if str(r.get('phone_correct', '')).strip() == 'X':
                        total_errors += 1
                    if r.get("satisfaction") == "满意":
                        satisfaction_count += 1
                    
            c_cnt = c_cnt if c_cnt > 0 else len(g_rows)
            prog_score = max(20.0 - total_errors * 0.5, 0.0)
            effect_score = (satisfaction_count / c_cnt * 10.0) if c_cnt > 0 else 10.0
            
            hierarchy[t_name][v_name].append({
                "group": g_name,
                "prog_score": prog_score,
                "effect_score": effect_score
            })
            
        # 2. 按照实际有抽样数据的乡镇排序列出块结构
        # 规则：村得分由各组得分平均值，乡镇得分为各村平均值
        if all_townships:
            sampled_townships = [t for t in all_townships if t in hierarchy]
        else:
            sampled_townships = list(hierarchy.keys())

        township_blocks = []
        current_row = 3
        total_rows_needed = 0

        for ts_idx, t_name in enumerate(sampled_townships):
            v_dict = hierarchy.get(t_name, {})
            if not v_dict:
                continue

            ts_start_row = current_row
            v_blocks = []
            
            for v_name, g_list in v_dict.items():
                if not g_list:
                    continue
                v_start_row = current_row
                g_count = len(g_list)
                v_end_row = current_row + g_count - 1
                
                # 村得分为各组得分平均值
                v_prog = sum(g["prog_score"] for g in g_list) / g_count
                v_effect = sum(g["effect_score"] for g in g_list) / g_count
                
                v_blocks.append({
                    "village": v_name,
                    "v_prog": v_prog,
                    "v_effect": v_effect,
                    "start_row": v_start_row,
                    "end_row": v_end_row,
                    "groups": g_list
                })
                current_row += g_count
                total_rows_needed += g_count

            ts_end_row = current_row - 1
            # 乡镇得分为各村得分平均值
            if v_blocks:
                town_prog = sum(vb["v_prog"] for vb in v_blocks) / len(v_blocks)
                town_effect = sum(vb["v_effect"] for vb in v_blocks) / len(v_blocks)
            else:
                town_prog = 20.0
                town_effect = 10.0

            township_blocks.append({
                "ts_no": str(ts_idx + 1),
                "township": t_name,
                "town_prog": town_prog,
                "town_effect": town_effect,
                "start_row": ts_start_row,
                "end_row": ts_end_row,
                "villages": v_blocks
            })

        N = total_rows_needed
        # 表格初始结构：Row 1 和 2 是表头，预留数据行数 = t.Rows.Count - 2
        current_reserved = t.Rows.Count - 2
        if N > current_reserved:
            last_row = t.Rows.Count
            t.Cell(last_row, 1).Select()
            word.Selection.InsertRowsBelow(N - current_reserved)
        elif N < current_reserved:
            for _ in range(current_reserved - N):
                last_row = t.Rows.Count
                t.Cell(last_row, 1).Select()
                word.Selection.Rows.Delete()

        # 3. 填充全部单元格
        # 对于即将纵向合并的列：
        # - 镇级（列 1~4）：仅在 ts_start_row 填充文本，其余行留空
        # - 村级（列 5~7）：仅在 v_start_row 填充文本，其余行留空
        # - 组级（列 8~10）：每行填充对应的组信息与得分
        for ts_b in township_blocks:
            for vb in ts_b["villages"]:
                for g_idx, g_item in enumerate(vb["groups"]):
                    r_idx = vb["start_row"] + g_idx
                    
                    # 镇级列 (1~4)
                    if r_idx == ts_b["start_row"]:
                        t.Cell(r_idx, 1).Range.Text = ts_b["ts_no"]
                        t.Cell(r_idx, 2).Range.Text = ts_b["township"]
                        t.Cell(r_idx, 3).Range.Text = format_score(ts_b["town_prog"])
                        t.Cell(r_idx, 4).Range.Text = format_score(ts_b["town_effect"])
                    else:
                        t.Cell(r_idx, 1).Range.Text = ""
                        t.Cell(r_idx, 2).Range.Text = ""
                        t.Cell(r_idx, 3).Range.Text = ""
                        t.Cell(r_idx, 4).Range.Text = ""

                    # 村级列 (5~7)
                    if r_idx == vb["start_row"]:
                        t.Cell(r_idx, 5).Range.Text = vb["village"]
                        t.Cell(r_idx, 6).Range.Text = format_score(vb["v_prog"])
                        t.Cell(r_idx, 7).Range.Text = format_score(vb["v_effect"])
                    else:
                        t.Cell(r_idx, 5).Range.Text = ""
                        t.Cell(r_idx, 6).Range.Text = ""
                        t.Cell(r_idx, 7).Range.Text = ""

                    # 组级列 (8~10)
                    t.Cell(r_idx, 8).Range.Text = g_item["group"]
                    t.Cell(r_idx, 9).Range.Text = format_score(g_item["prog_score"])
                    t.Cell(r_idx, 10).Range.Text = format_score(g_item["effect_score"])

        # 4. 逆序执行单元格纵向合并 (先合并村级列 7,6,5，再合并镇级列 4,3,2,1)
        # 倒序遍历村块执行合并
        all_village_blocks = []
        for ts_b in township_blocks:
            for vb in ts_b["villages"]:
                all_village_blocks.append(vb)

        for vb in reversed(all_village_blocks):
            if vb["end_row"] > vb["start_row"]:
                for c in [7, 6, 5]:
                    try:
                        t.Cell(vb["start_row"], c).Merge(t.Cell(vb["end_row"], c))
                        t.Cell(vb["start_row"], c).VerticalAlignment = 1
                        t.Cell(vb["start_row"], c).Range.ParagraphFormat.Alignment = 1
                    except Exception as me:
                        print(f"Merge village cells error at {vb['start_row']}-{vb['end_row']} col {c}: {me}")

        # 倒序遍历乡镇块执行合并
        for ts_b in reversed(township_blocks):
            if ts_b["end_row"] > ts_b["start_row"]:
                for c in [4, 3, 2, 1]:
                    try:
                        t.Cell(ts_b["start_row"], c).Merge(t.Cell(ts_b["end_row"], c))
                        t.Cell(ts_b["start_row"], c).VerticalAlignment = 1
                        t.Cell(ts_b["start_row"], c).Range.ParagraphFormat.Alignment = 1
                    except Exception as me:
                        print(f"Merge township cells error at {ts_b['start_row']}-{ts_b['end_row']} col {c}: {me}")

        doc.SaveAs2(FileName=out_path, FileFormat=0)
        doc.Close(0)
        doc = None
        word.Quit()
        word = None
        return f"/api/download?file=downloads/{out_filename}"
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

# ================= 自查整改（附件12 / 附件13） =================

WAIYE_FLAG_LABELS = [
    ("area_acknowledged", "面积不认可"),
    ("rights_correct", "权属不正确"),
    ("bound_correct", "四至不正确"),
    ("member_qualified", "成员不符合"),
    ("self_verified", "非本人核实"),
    ("self_signed", "非本人签名"),
    ("phone_correct", "联系电话不正确"),
]

def _build_rectify_rows(neiye_form, waiye_rows, township_name):
    rows = []
    
    MAJOR_NEIYE = [
        "未制定方案", "直接套用上级方案", "制定程序不合法", 
        "未召开会议", "未公示工作组名单", "参会人数不足法定数量", 
        "没有延包方案", "延包方案未上报", "延包方案未公示", "未召开会议讨论延包方案", 
        "合同版本格式不正确", "合同网签率未达到95%", "没有地块示意图", 
        "档案整理第三方无涉密档案整理资质", "档案资料收集不齐全", "档案分类不符合要求", 
        "档号与归档章不一致", "档案变数字化瑕疵", "姓名著录错误"
    ]
    SEVERE_NEIYE = [
        "支付不规范", "支付不及时", "经费没有县级兜底", "没有进行摸底", 
        "摸底表农户未签署", "摸底表中没有表达延包意愿", "摸底表其它签署不齐全", 
        "特殊人员摸底不清或未统计", "户变化未统计", "矛盾纠纷未登记或处理不当", 
        "承包地变化未摸清", "没有应确尽确", "没有公示材料", "没有公示不足15天", "没有公示或不足15天", "公示不足15天",
        "公示结果未确认", "未进行信息共享", "未与不动产登记部门有序衔接", 
        "未保障特殊群体权益", "未保障无地户权益", "没有应收尽收", 
        "采用不正当方式隐匿消亡户", "违背农户意愿强行推进", "确权确股不确地手续不齐全", 
        "小调整比率过大或手续不齐全", "打乱重分", "违法调整或收回承包地", 
        "未建立矛盾纠纷处置机制", "未建立舆情处置办法", "没有矛盾纠纷处理台账"
    ]
    
    MAJOR_WAIYE = ["权属不正确", "成员不符合"]
    SEVERE_WAIYE = ["非本人签名", "面积不认可"]
    
    def get_level(problem_desc, is_neiye=True):
        if is_neiye:
            return get_issue_level_3tier(problem_desc)
        else:
            return get_waiye_issue_level(problem_desc)

    # 内业问题：先归一化，兼容旧数据中字段为字符串的情况
    def _norm_list(v):
        if isinstance(v, str): return [v] if v else []
        if isinstance(v, list): return v
        return []
    
    if isinstance(neiye_form, dict):
        # 列表型问题字段
        for key, val in neiye_form.items():
            items = _norm_list(val)
            for item in items:
                if item:
                    item_str = str(item)
                    rows.append({
                        "source": "内业",
                        "level": get_level(item_str, is_neiye=True),
                        "desc": f"{township_name} {item_str}",
                        "scope": "",
                        "unit": township_name,
                    })
        # 数量型问题字段：未保障特殊/无地户权益、消亡户应收尽收、不正当隐匿消亡户等
        policy_fields = [
            ("policy_2_1", "未保障特殊群体权益"),
            ("policy_2_2", "未保障无地户权益"),
            ("policy_2_3", "没有统计（关注）特殊群体"),
            ("policy_3_1", "没有应收尽收"),
            ("policy_3_2", "采用不正当方式隐匿消亡户"),
            ("policy_3_3", "违规处置消亡土地"),
            ("policy_3_4", "没有统计消亡户"),
            ("policy_3_5", "没有分清实际消亡户和伪消亡户"),
        ]
        for key, label in policy_fields:
            cnt = int(neiye_form.get(key, 0) or 0)
            if cnt > 0:
                rows.append({
                    "source": "内业",
                    "level": get_level(label, is_neiye=True),
                    "desc": f"{township_name} {label}（{cnt}起）",
                    "scope": str(cnt),
                    "unit": township_name,
                })
    # 外业问题：waiye_samples 中按户和地块分组
    CBF_ERRORS = [
        ("phone_correct", "联系电话不正确"),
        ("member_qualified", "成员不符合"),
        ("rights_correct", "权属不正确"),
        ("self_signed", "非本人签名"),
    ]
    DK_ERRORS = [
        ("bound_correct", "四至不正确"),
        ("area_acknowledged", "面积不认可"),
        ("self_verified", "非本人核实"),
    ]

    from collections import defaultdict
    waiye_groups = defaultdict(list)
    for r in (waiye_rows or []):
        cbf_key = (r.get("village_name", ""), r.get("group_name", ""), r.get("cbfmc", ""), r.get("cbfbm_short", ""))
        waiye_groups[cbf_key].append(r)

    for (village_name, group_name, cbfmc, cbfbm_short), group_rows in waiye_groups.items():
        first_r = group_rows[0]
        cbf_failed = [lbl for key, lbl in CBF_ERRORS if str(first_r.get(key, "")).strip() == "X"]
        
        dk_failed_list = []
        for r in group_rows:
            dk_failed = [lbl for key, lbl in DK_ERRORS if str(r.get(key, "")).strip() == "X"]
            if dk_failed:
                dk_name = r.get("dkbm_short", "") or r.get("dkmc", "")
                dk_failed_list.append(f"{dk_name}地块，{'、'.join(dk_failed)}")
                
        if cbf_failed or dk_failed_list:
            cbf_suffix = f"({cbfbm_short})" if cbfbm_short else ""
            loc = f"{township_name}{village_name}{group_name} {cbfmc}户{cbf_suffix}"
            desc_parts = []
            if cbf_failed:
                desc_parts.append(f"承包方核查问题有：{'，'.join(cbf_failed)}。")
            if dk_failed_list:
                desc_parts.append(f"地块核查问题有：{'；'.join(dk_failed_list)}。")
                
            desc_str = "\n".join(desc_parts)
            lvl = get_level(desc_str, is_neiye=False)
            
            rows.append({
                "source": "外业",
                "level": lvl,
                "desc": f"{loc}，{desc_str}",
                "scope": "",
                "unit": village_name or township_name,
            })
            
    if not rows:
        rows.append({
            "source": "",
            "level": "",
            "desc": "经自查，暂未发现需整改的问题",
            "scope": "",
            "unit": township_name,
        })
    return rows

def export_rectify_att12(township_name):
    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0

        base_dir = get_base_dir()
        tpl = os.path.join(base_dir, "附件", "附件12.doc")
        clean_ts = sanitize_filename(township_name)
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_path = os.path.join(base_dir, "backend", "downloads", f"附件12_整改通知书_{clean_ts}.doc")
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        shutil.copy(tpl, out_path)

        doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)

        from database import get_county_and_townships_sync
        county_info, _ = get_county_and_townships_sync()
        county_name = county_info.get("name", "全椒县")
        replace_common_bookmarks(doc, county_name)

        # 替换标题中的"（模版）"，用 Find 保留段落格式
        f12 = doc.Content.Find
        f12.ClearFormatting()
        f12.Replacement.ClearFormatting()
        f12.Execute(FindText="（模版）", ReplaceWith="", Replace=2)
        f12.Execute(FindText="（模板）", ReplaceWith="", Replace=2)

        # 替换书签 XJQYMC 为乡镇名称
        if doc.Bookmarks.Exists("XJQYMC"):
            doc.Bookmarks("XJQYMC").Range.Text = township_name

        doc.SaveAs2(FileName=out_path, FileFormat=0)
        doc.Close(0)
        doc = None
        word.Quit()
        word = None
        return f"/api/download?file=downloads/附件12_整改通知书_{clean_ts}.doc"
    except Exception as e:
        print("export_rectify_att12 error:", e)
        if doc:
            try: doc.Close(0)
            except: pass
        if word:
            try: word.Quit()
            except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()

def export_rectify_att13(township_name, neiye_form, waiye_rows):
    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0

        base_dir = get_base_dir()
        tpl = os.path.join(base_dir, "附件", "附件13.doc")
        clean_ts = sanitize_filename(township_name)
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_path = os.path.join(base_dir, "backend", "downloads", f"附件13_问题整改销号台账_{clean_ts}.doc")
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        shutil.copy(tpl, out_path)

        doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
        from database import get_county_and_townships_sync
        county_info, _ = get_county_and_townships_sync()
        county_name = county_info.get("name", "全椒县")
        replace_common_bookmarks(doc, county_name)

        t = doc.Tables(1)

        # 删除模板中的空白数据行，仅保留表头
        while t.Rows.Count > 1:
            t.Rows(t.Rows.Count).Delete()

        data_rows = _build_rectify_rows(neiye_form, waiye_rows, township_name)

        for i, item in enumerate(data_rows):
            # 始终选中当前最后一行，在其下方插入新行，保证数据顺序正确
            t.Rows(t.Rows.Count).Select()
            word.Selection.InsertRowsBelow(1)
            r = i + 2
            
            # 取消新建行的表头属性（防止从第一行继承导致全表变成表头无法跨页重复）
            t.Rows(r).HeadingFormat = False
            
            row_rng = t.Rows(r).Range
            row_rng.ParagraphFormat.Alignment = 1    # 居中
            row_rng.Font.Bold = False                # 取消加粗
            for c in range(1, 17):
                t.Cell(r, c).Range.Text = ""
            t.Cell(r, 1).Range.Text = str(i + 1)                       # 序号
            t.Cell(r, 2).Range.Text = item["source"]                   # 问题来源
            t.Cell(r, 3).Range.Text = item.get("level", "一般")        # 问题等级
            t.Cell(r, 4).Range.Text = item["desc"]                     # 问题具体描述
            t.Cell(r, 5).Range.Text = item.get("scope", "")            # 涉及资料/农户数量
            t.Cell(r, 6).Range.Text = item.get("unit", "")             # 整改责任单位
            t.Cell(r, 9).Range.Text = "对照问题逐项整改，补齐材料，规范程序"  # 整改措施
            # 列13 复核情况、列15 销号状态保持为空

        # 在所有数据行插入完毕后，重新设置表头重复标题行（确保生效）
        t.Rows(1).HeadingFormat = True

        doc.SaveAs2(FileName=out_path, FileFormat=0)
        doc.Close(0)
        doc = None
        word.Quit()
        word = None
        return f"/api/download?file=downloads/附件13_问题整改销号台账_{clean_ts}.doc"
    except Exception as e:
        print("export_rectify_att13 error:", e)
        if doc:
            try: doc.Close(0)
            except: pass
        if word:
            try: word.Quit()
            except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()

# 严重错误清单 (35项)
SEVERE_ISSUES = {
    "未制定方案", "方案未盖章或非红头", "直接套用上级方案", "制定程序不合法", "方案缺少",
    "支付不规范", "支付不及时", "经费没有县级兜底",
    "未召开村民会议", "未选举产生理事会", "未公示理事会名单", "公示时间不足3天",
    "参会人数不足法定数量", "违规召开村民会议", "理事会成员非本集体经济组织",
    "没有进行摸底", "没有延包方案草案", "没有延包方案", "延包方案未上报", "延包方案未公示",
    "未召开会议讨论延包方案", "延包方案上报与通过会议时间顺序不正确",
    "延包方案与工作方案混淆", "理事会与工作领导小组混淆",
    "没有公示材料", "没有公示或公示不足15天", "公示不足15天",
    "合同版本格式不正确", "合同网签率未达到95%", "没有地块示意图",
    "未进行信息共享", "未与不动产登记部门有序衔接", "承包地块间重叠", "承包地块与宅基地重叠",
    "档案整理第三方无涉密档案整理资质", "没有进行档案验收", "档案验收不符合相关标准"
}

# 较重错误清单 (16项)
MAJOR_ISSUES = {
    "打乱重分", "违法调整或收回承包地", "没有小调整统计资料或说明",
    "未保障特殊群体权益", "未保障无地户权益", "没有统计（关注）特殊群体",
    "没有应收尽收", "采用不正当方式隐匿消亡户", "违规处置消亡土地", "没有统计消亡户", "没有分清实际消亡户和伪消亡户",
    "未建立矛盾纠纷处置机制", "未建立舆情处置办法", "没有矛盾纠纷处理台账",
    "矛盾纠纷处理台账填写不规范", "没有本级处理的矛盾纠纷处理记录"
}

# 外业核查错误等级规则
SEVERE_WAIYE = ["非本人签名", "面积不认可"]
MAJOR_WAIYE = ["权属不正确", "成员不符合"]

def get_waiye_issue_level(desc_text: str) -> str:
    """外业核查等级评定：严重 / 较重 / 一般"""
    for s in SEVERE_WAIYE:
        if s in desc_text:
            return "严重"
    for m in MAJOR_WAIYE:
        if m in desc_text:
            return "较重"
    return "一般"

def get_issue_level_3tier(text_val: str) -> str:
    """根据问题描述匹配严重、较重、一般（未列出的默认为一般）"""
    for s in SEVERE_ISSUES:
        if s in text_val:
            return "严重"
    for m in MAJOR_ISSUES:
        if m in text_val:
            return "较重"
    return "一般"

def map_neiye_item_to_category_and_sub(key: str, item_text: str):
    """映射内业问题键名与描述到错误大类与验收子内容"""
    if key.startswith("mech_1"):
        return "机制运行", "配套延包政策文件"
    elif key.startswith("mech_2"):
        return "机制运行", "经费保障"
    elif key.startswith("mech_3"):
        return "机制运行", "宣传"
    elif key.startswith("mech_4"):
        return "机制运行", "培训"
    elif key.startswith("prog_1"):
        return "程序规范", "成立机构"
    elif key.startswith("prog_2"):
        return "程序规范", "摸底核实"
    elif key.startswith("prog_3"):
        return "程序规范", "制定方案"
    elif key.startswith("prog_4"):
        return "程序规范", "调查公示"
    elif key.startswith("prog_5"):
        return "程序规范", "签订合同"
    elif key.startswith("prog_6"):
        return "程序规范", "完善证书"
    elif key.startswith("prog_7"):
        return "程序规范", "资料归档"
    elif key.startswith("policy_1"):
        return "政策落实", "“大稳定、小调整”落实情况"
    elif key.startswith("policy_2"):
        return "政策落实", "保障土地承包权益"
    elif key.startswith("policy_3"):
        return "政策落实", "依法收回消亡户承包地"
    elif key.startswith("policy_4"):
        return "政策落实", "严格机动地和新增耕地管理"
    elif key.startswith("policy_5"):
        return "政策落实", "从严掌握确权确股不确地"
    elif key.startswith("effect"):
        return "工作成效", "加强风险防范"
    return "内业核查", "综合检查"

def export_county_issue_feedback_summary(county_name=None):
    """全县问题反馈记录表汇总快捷导出（自查整改模块调用，包含内业核查与外业核查）"""
    return export_issue_feedback_summary_by_level(level="county", county_name=county_name, include_waiye=True)

def export_issue_feedback_summary_by_level(
    level: str = "county",
    qsdwdm: str = "",
    township_name: str = "",
    village_name: str = "",
    qsdwmc: str = "",
    county_name: str = None,
    current_form_data: dict = None,
    include_waiye: bool = True
) -> str:
    """
    按核查对象层级（县级 / 乡镇级 / 行政村级）精准导出《问题反馈记录表汇总.doc》：
    - 模板文件：附件/XX县问题反馈记录表汇总.doc
    - 横向 A4 版式，7 列：序号、所在行政区、错误大类、验收内容、错误等级、错误描述、照片或其它证据
    - 错误等级分三等：严重、较重、一般，未列出的默认为“一般”
    - include_waiye=False 时（内业核查模块调用）：仅导出内业核查问题，不包含外业核查；
    - include_waiye=True 时（自查整改模块调用）：综合汇总内业核查与外业核查发现的全部问题。
    """
    import os, shutil, win32com.client, pythoncom
    from PIL import Image, ImageOps
    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        from database import get_county_and_townships_sync, load_config, build_sync_url, current_db_ctx
        from sqlalchemy import create_engine, text
        
        county_info, _ = get_county_and_townships_sync()
        if not county_name:
            county_name = county_info.get("name", "全椒县")

        base_dir = get_base_dir()
        downloads_dir = os.path.join(base_dir, "backend", "downloads")
        os.makedirs(downloads_dir, exist_ok=True)

        clean_cname = sanitize_filename(county_name)
        clean_ts = sanitize_filename(township_name or "")
        clean_vn = sanitize_filename(village_name or "")

        # 根据层级决定输出文件名和文档大标题
        if level == "village":
            loc_prefix = f"{clean_cname}{clean_ts}{clean_vn}" if (clean_ts or clean_vn) else clean_cname
            out_filename = f"{loc_prefix}问题反馈记录表汇总.doc"
            title_text = f"【{clean_cname}{clean_ts}{clean_vn}】问题反馈记录表汇总"
        elif level == "township":
            loc_prefix = f"{clean_cname}{clean_ts}" if clean_ts else clean_cname
            out_filename = f"{loc_prefix}问题反馈记录表汇总.doc"
            title_text = f"【{clean_cname}{clean_ts}】问题反馈记录表汇总"
        else: # county
            out_filename = f"{clean_cname}问题反馈记录表汇总.doc"
            title_text = f"{clean_cname}问题反馈记录表汇总"

        out_path = os.path.join(downloads_dir, out_filename)
        tpl_path = os.path.join(base_dir, "附件", "XX县问题反馈记录表汇总.doc")

        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        shutil.copy(tpl_path, out_path)

        # 1. 查询全部内业与外业问题数据
        cfg = load_config()
        cur_db = current_db_ctx.get() or cfg.get("db_name", "quanjiao")
        sync_url = build_sync_url(cfg, cur_db)
        sync_engine = create_engine(sync_url)

        all_issues = []

        with sync_engine.connect() as conn:
            # (1) 准备内业核查记录并根据层级过滤
            res_nei = conn.execute(text("SELECT qsdwdm, qsdwmc, level, form_data FROM neiye_records ORDER BY qsdwdm"))
            all_nei_rows = res_nei.fetchall()

            # 过滤内业记录
            target_nei_rows = []
            for r in all_nei_rows:
                r_dm, r_mc, r_lvl, r_fd = str(r[0]), str(r[1] or ""), str(r[2] or ""), r[3] or {}
                if level == "village":
                    # 仅保留该行政村的记录
                    if r_dm == str(qsdwdm) or (village_name and village_name in r_mc):
                        target_nei_rows.append((r_dm, r_mc, r_lvl, r_fd))
                elif level == "township":
                    # 保留乡镇本级及该乡镇下属各村
                    if township_name and (township_name in r_mc or r_dm.startswith(str(qsdwdm)[:9])):
                        target_nei_rows.append((r_dm, r_mc, r_lvl, r_fd))
                else: # county
                    target_nei_rows.append((r_dm, r_mc, r_lvl, r_fd))

            # 若当前正在编辑该对象且传入了 current_form_data，优先覆盖替换为最新表单数据
            if current_form_data and qsdwdm:
                replaced = False
                new_target_rows = []
                for (r_dm, r_mc, r_lvl, r_fd) in target_nei_rows:
                    if r_dm == str(qsdwdm):
                        new_target_rows.append((r_dm, qsdwmc or r_mc, level, current_form_data))
                        replaced = True
                    else:
                        new_target_rows.append((r_dm, r_mc, r_lvl, r_fd))
                if not replaced:
                    new_target_rows.insert(0, (str(qsdwdm), qsdwmc or (village_name or township_name or county_name), level, current_form_data))
                target_nei_rows = new_target_rows

            for r in target_nei_rows:
                q_dm, q_mc, lvl, fd = r[0], r[1], r[2], r[3] or {}
                # 规范所在行政区名称
                if lvl == "county" or q_dm == county_info.get("code"):
                    area_name = county_name
                elif lvl == "township":
                    t_name = q_mc.replace("(乡镇级 - 机制运行)", "").replace("(乡镇级 - 机制与成效)", "").replace("乡镇级", "").strip()
                    area_name = f"{county_name}{t_name}" if not t_name.startswith(county_name) else t_name
                else: # village
                    if " - " in q_mc:
                        t_part, v_part = q_mc.split(" - ", 1)
                        t_part, v_part = t_part.strip(), v_part.strip()
                        area_name = f"{county_name}{t_part}{v_part}"
                    else:
                        area_name = f"{county_name}{q_mc}"

                evidences = fd.get("evidences", {})

                # 列表型内业问题
                for k, v in fd.items():
                    if isinstance(v, list) and k != "evidences":
                        cat, sub = map_neiye_item_to_category_and_sub(k, "")
                        for item in v:
                            if item:
                                item_str = str(item).strip()
                                level_str = get_issue_level_3tier(item_str)
                                
                                p_list = []
                                if item_str in evidences:
                                    for img_obj in evidences[item_str]:
                                        u = img_obj.get("url") if isinstance(img_obj, dict) else str(img_obj)
                                        if u: p_list.append(u)

                                all_issues.append({
                                    "area": area_name,
                                    "category": cat,
                                    "sub_content": sub,
                                    "level": level_str,
                                    "desc": item_str,
                                    "evidences": p_list
                                })
                
                # 数量型内业问题
                policy_fields = [
                    ("policy_2_1", "未保障特殊群体权益", "policy_2"),
                    ("policy_2_2", "未保障无地户权益", "policy_2"),
                    ("policy_2_3", "没有统计（关注）特殊群体", "policy_2"),
                    ("policy_3_1", "没有应收尽收", "policy_3"),
                    ("policy_3_2", "采用不正当方式隐匿消亡户", "policy_3"),
                    ("policy_3_3", "违规处置消亡土地", "policy_3"),
                    ("policy_3_4", "没有统计消亡户", "policy_3"),
                    ("policy_3_5", "没有分清实际消亡户和伪消亡户", "policy_3"),
                ]
                for p_key, p_label, p_grp in policy_fields:
                    cnt = int(fd.get(p_key, 0) or 0)
                    if cnt > 0:
                        cat, sub = map_neiye_item_to_category_and_sub(p_grp, p_label)
                        level_str = get_issue_level_3tier(p_label)
                        p_list = []
                        if p_label in evidences:
                            for img_obj in evidences[p_label]:
                                u = img_obj.get("url") if isinstance(img_obj, dict) else str(img_obj)
                                if u: p_list.append(u)
                        all_issues.append({
                            "area": area_name,
                            "category": cat,
                            "sub_content": sub,
                            "level": level_str,
                            "desc": f"{p_label}（{cnt}起）",
                            "evidences": p_list
                        })

            # (2) 查询外业核查抽检不合格项（按层级精确过滤，仅在 include_waiye=True 时归集）
            if include_waiye:
                wai_conds = []
                wai_params = {}
                if level == "village" and (village_name or township_name):
                    if township_name:
                        wai_conds.append("township_name = :tn")
                        wai_params["tn"] = township_name
                    if village_name:
                        wai_conds.append("village_name = :vn")
                        wai_params["vn"] = village_name
                elif level == "township" and township_name:
                    wai_conds.append("township_name = :tn")
                    wai_params["tn"] = township_name

                where_clause = ("WHERE " + " AND ".join(wai_conds)) if wai_conds else ""

                res_wai = conn.execute(text(f"""
                    SELECT township_name, village_name, group_name,
                           SUM(CASE WHEN area_acknowledged = 'X' THEN 1 ELSE 0 END) as area_err,
                           SUM(CASE WHEN rights_correct = 'X' THEN 1 ELSE 0 END) as rights_err,
                           SUM(CASE WHEN bound_correct = 'X' THEN 1 ELSE 0 END) as bound_err,
                           SUM(CASE WHEN member_qualified = 'X' THEN 1 ELSE 0 END) as member_err,
                           SUM(CASE WHEN self_verified = 'X' THEN 1 ELSE 0 END) as verify_err,
                           SUM(CASE WHEN self_signed = 'X' THEN 1 ELSE 0 END) as sign_err,
                           SUM(CASE WHEN phone_correct = 'X' THEN 1 ELSE 0 END) as phone_err
                    FROM waiye_samples
                    {where_clause}
                    GROUP BY township_name, village_name, group_name
                    HAVING (SUM(CASE WHEN area_acknowledged = 'X' THEN 1 ELSE 0 END) +
                            SUM(CASE WHEN rights_correct = 'X' THEN 1 ELSE 0 END) +
                            SUM(CASE WHEN bound_correct = 'X' THEN 1 ELSE 0 END) +
                            SUM(CASE WHEN member_qualified = 'X' THEN 1 ELSE 0 END) +
                            SUM(CASE WHEN self_verified = 'X' THEN 1 ELSE 0 END) +
                            SUM(CASE WHEN self_signed = 'X' THEN 1 ELSE 0 END) +
                            SUM(CASE WHEN phone_correct = 'X' THEN 1 ELSE 0 END)) > 0
                    ORDER BY township_name, village_name, group_name
                """), wai_params)
                for wr in res_wai.fetchall():
                    tn, vn, gn = wr[0], wr[1], wr[2]
                    area_err, rights_err, bound_err, member_err, verify_err, sign_err, phone_err = wr[3], wr[4], wr[5], wr[6], wr[7], wr[8], wr[9]
                    w_area = f"{county_name}{tn or ''}{vn or ''}{gn or ''}"
                    
                    fails = []
                    if rights_err > 0:  fails.append(f"权属不正确({rights_err}宗)")
                    if member_err > 0:  fails.append(f"成员不符合({member_err}宗)")
                    if bound_err > 0:   fails.append(f"四至不正确({bound_err}宗)")
                    if area_err > 0:    fails.append(f"面积不认可({area_err}宗)")
                    if sign_err > 0:    fails.append(f"非本人签名({sign_err}宗)")
                    if verify_err > 0:  fails.append(f"非本人核实({verify_err}宗)")
                    if phone_err > 0:   fails.append(f"联系电话不正确({phone_err}宗)")

                    if fails:
                        full_desc = f"{gn}外业实地抽查发现：" + "、".join(fails)
                        all_issues.append({
                            "area": w_area,
                            "category": "程序规范",
                            "sub_content": "外业实地核查",
                            "level": get_waiye_issue_level(full_desc),
                            "desc": full_desc,
                            "evidences": []
                        })

        # 2. 调用 Word COM 打开并填充文档
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        word.ScreenUpdating = False

        doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)

        # 替换大标题中的县名或区划
        rng_doc = doc.Content
        f = rng_doc.Find
        f.ClearFormatting()
        f.Replacement.ClearFormatting()
        f.Execute("XX县（市）问题反馈记录表汇总", False, False, False, False, False, True, 1, False, title_text, 2)
        f.Execute("XX县问题反馈记录表汇总", False, False, False, False, False, True, 1, False, title_text, 2)
        f.Execute("XX县（市）", False, False, False, False, False, True, 1, False, f"{county_name}", 2)
        f.Execute("XX县", False, False, False, False, False, True, 1, False, f"{county_name}", 2)

        t = doc.Tables(1)
        
        N_issues = len(all_issues)
        if N_issues == 0:
            while t.Rows.Count > 2:
                t.Rows(3).Delete()
            t.Cell(2, 1).Range.Text = "1"
            t.Cell(2, 2).Range.Text = (title_text.replace("问题反馈记录表汇总", "").replace("【", "").replace("】", "") or county_name)
            t.Cell(2, 3).Range.Text = "/"
            t.Cell(2, 4).Range.Text = "/"
            t.Cell(2, 5).Range.Text = "一般"
            t.Cell(2, 6).Range.Text = "经核查，当前范围内未发现需整改的问题项。"
            t.Cell(2, 7).Range.Text = ""
        else:
            while t.Rows.Count > 2:
                t.Rows(3).Delete()
            if t.Rows.Count < 2:
                t.Rows.Add()
            if N_issues > 1:
                t.Rows(2).Select()
                word.Selection.InsertRowsBelow(N_issues - 1)

            for i, itm in enumerate(all_issues, 1):
                r_idx = i + 1
                row_obj = t.Rows(r_idx)
                row_obj.HeadingFormat = False
                row_obj.Range.Font.Bold = False
                row_obj.Range.Font.Name = "仿宋"
                row_obj.Range.Font.Size = 9.5

                # 序号、大类、等级居中
                t.Cell(r_idx, 1).Range.ParagraphFormat.Alignment = 1
                t.Cell(r_idx, 3).Range.ParagraphFormat.Alignment = 1
                t.Cell(r_idx, 5).Range.ParagraphFormat.Alignment = 1

                t.Cell(r_idx, 1).Range.Text = str(i)
                t.Cell(r_idx, 2).Range.Text = itm.get("area", "")
                t.Cell(r_idx, 3).Range.Text = itm.get("category", "")
                t.Cell(r_idx, 4).Range.Text = itm.get("sub_content", "")
                
                # 错误等级着色
                lvl = itm.get("level", "一般")
                c5 = t.Cell(r_idx, 5)
                c5.Range.Text = lvl
                c5.Range.Font.Bold = True
                if lvl == "严重":
                    c5.Range.Font.Color = 255 # 红色
                elif lvl == "较重":
                    c5.Range.Font.Color = 39423 # 橙褐色
                else:
                    c5.Range.Font.Color = 2276885 # 深绿色

                t.Cell(r_idx, 6).Range.Text = itm.get("desc", "")

                # 照片或其它证据单元格
                ev_paths = itm.get("evidences", [])
                c7 = t.Cell(r_idx, 7)
                c7.Range.ParagraphFormat.Alignment = 1
                valid_p = []
                for p_raw in ev_paths:
                    if p_raw.startswith("/uploads/"):
                        rel_p = p_raw.lstrip("/")
                    elif "file=" in p_raw:
                        rel_p = p_raw.split("file=")[-1].lstrip("/")
                    else:
                        rel_p = os.path.join("uploads", os.path.basename(p_raw))
                    cand = os.path.join(base_dir, "backend", rel_p)
                    if os.path.exists(cand):
                        valid_p.append(cand)

                if valid_p:
                    c7.Range.Text = ""
                    for p_abs in valid_p[:2]: # 最多嵌入前2张佐证缩略图
                        try:
                            with Image.open(p_abs) as im:
                                im = ImageOps.exif_transpose(im)
                                img_w, img_h = im.size

                            max_dim_pt = 5.5 * 72.0 / 2.54
                            scale = max_dim_pt / max(img_w, img_h, 1)
                            target_w = img_w * scale
                            target_h = img_h * scale

                            shape = c7.Range.InlineShapes.AddPicture(FileName=os.path.abspath(p_abs), LinkToFile=False, SaveWithDocument=True)
                            shape.LockAspectRatio = -1
                            shape.Width = target_w
                            shape.Height = target_h
                        except Exception as pe:
                            print(f"插入佐证图片异常: {pe}")
                else:
                    c7.Range.Text = ""

        # 确保表头在跨页时重复显示
        t.Rows(1).HeadingFormat = True

        # 3. 映射并填充检查者 (jcz) 与 复核者 (fhz) 书签
        jcz_name = ""
        fhz_name = ""
        if current_form_data:
            jcz_name = str(current_form_data.get("jcz_name") or "").strip()
            fhz_name = str(current_form_data.get("fhz_name") or "").strip()

        # 若未从 current_form_data 获取到，则尝试从目标内业记录中提取
        if not jcz_name or not fhz_name:
            for (_, _, _, r_fd) in target_nei_rows:
                if not jcz_name and r_fd.get("jcz_name"):
                    jcz_name = str(r_fd.get("jcz_name")).strip()
                if not fhz_name and r_fd.get("fhz_name"):
                    fhz_name = str(r_fd.get("fhz_name")).strip()
                if jcz_name and fhz_name:
                    break

        if doc.Bookmarks.Exists("jcz"):
            try:
                doc.Bookmarks("jcz").Range.Text = f" {jcz_name} " if jcz_name else ""
            except Exception as e_jcz:
                print(f"填充 jcz 书签异常: {e_jcz}")

        if doc.Bookmarks.Exists("fhz"):
            try:
                doc.Bookmarks("fhz").Range.Text = f" {fhz_name} " if fhz_name else ""
            except Exception as e_fhz:
                print(f"填充 fhz 书签异常: {e_fhz}")

        doc.SaveAs2(FileName=out_path, FileFormat=0)
        doc.Close(0)
        doc = None
        word.Quit()
        word = None
        return f"/api/download?file=downloads/{out_filename}"
    except Exception as e:
        print("export_issue_feedback_summary_by_level error:", e)
        if doc:
            try: doc.Close(0)
            except: pass
        if word:
            try: word.Quit()
            except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()

def export_waiye_inquiry(data):
    import os, shutil, win32com.client, pythoncom
    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        
        base_dir = get_base_dir()
        tpl = os.path.join(base_dir, "附件", "询问笔录.doc")
        
        # 实际承包方名称用于文件名和书签 cbfmc
        real_cbfmc = str(data.get("cbfmc", "")).strip()
        clean_cbf = sanitize_filename(real_cbfmc)

        # 文件名前缀带上 XX镇XX村
        clean_ts = sanitize_filename(data.get("township_name", "") or "")
        clean_vn = sanitize_filename(data.get("village_name", "") or "")
        loc_parts = [p for p in [clean_ts, clean_vn] if p]
        loc_prefix = "".join(loc_parts)
        if loc_prefix:
            out_filename = f"附件_询问笔录_{loc_prefix}_{clean_cbf}.doc"
        else:
            out_filename = f"附件_询问笔录_{clean_cbf}.doc"

        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_path = os.path.join(base_dir, "backend", "downloads", out_filename)
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        shutil.copy(tpl, out_path)
        
        doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
        from database import get_county_and_townships_sync
        county_info, _ = get_county_and_townships_sync()
        county_name = county_info.get("name", "全椒县")
        replace_common_bookmarks(doc, county_name)

        fd = data.get("form_data", {})
        
        def _check(doc, target_text):
            f = doc.Content.Find
            f.ClearFormatting()
            f.Replacement.ClearFormatting()
            f.Execute("□" + target_text, False, False, False, False, False, True, 1, False, "☑" + target_text, 2)
            
        def _fill_bm(doc, bm_name, text, underline=False):
            if doc.Bookmarks.Exists(bm_name):
                rng = doc.Bookmarks(bm_name).Range
                if underline:
                    # Pad text with spaces for better visual underline
                    text = f" {text} "
                rng.Text = text
                if underline:
                    rng.Font.Underline = 1
                doc.Bookmarks.Add(Name=bm_name, Range=rng)
                
        import datetime
        now = datetime.datetime.now()
        
        _fill_bm(doc, "year", str(now.year), True)
        _fill_bm(doc, "month", str(now.month).zfill(2), True)
        _fill_bm(doc, "day", str(now.day).zfill(2), True)
        _fill_bm(doc, "hour", str(now.hour).zfill(2), True)
        _fill_bm(doc, "minite", str(now.minute).zfill(2), True)
        
        _fill_bm(doc, "xjqymc", data.get('township_name',''), True)
        _fill_bm(doc, "cjqymc", data.get('village_name',''), True)
        _fill_bm(doc, "zjqymc", data.get('group_name',''), True)
        
        # 书签 bxwr -> 页面基本信息获取 (被询问人姓名)
        bxwr_name = data.get("bxwr") or fd.get("bxwr") or fd.get("cbfmc") or real_cbfmc
        _fill_bm(doc, "bxwr", bxwr_name, True)
        
        # 书签 cbfmc -> 实际承包方名称
        _fill_bm(doc, "cbfmc", real_cbfmc, False)
        
        _fill_bm(doc, "xb", data.get('gender','男'), True)
        _fill_bm(doc, "lxdh", data.get('lxdh',''), True)
        
        place = fd.get('inquiry_place', '')
        if place in ['农户家中', '田间地头', '村委会']:
            _check(doc, place)
                    
        rel = fd.get('relationship', '')
        if rel in ['本人', '配偶', '子女']:
            _check(doc, rel)
        elif rel == '其他亲属':
            _check(doc, "其他亲属")
            
        _fill_bm(doc, "xwr", fd.get('inquirer',''), True)
        

        questions = fd.get('questions', [])
        xwnr_text = ""
        
        idx = 1
        for q in questions:
            if not q.get('checked'):
                continue
                
            q_text = q.get('q', '')
            xwnr_text += f"{idx}、{q_text}\r"
            
            opts = q.get('opts', [])
            ans = q.get('answer', '')
            has_desc = q.get('has_desc', False)
            desc_label = q.get('desc_label', '')
            desc = q.get('desc', '')
            
            ans_line = "答："
            if opts:
                opt_strs = []
                for o in opts:
                    if o == ans:
                        opt_strs.append(f"☑{o}")
                    else:
                        opt_strs.append(f"□{o}")
                ans_line += " ".join(opt_strs)
                
            if has_desc:
                if desc_label == "答：":
                    if not opts:
                        ans_line += f"{desc}"
                    else:
                        ans_line += f"  {desc}"
                else:
                    ans_line += f"  {desc_label}{desc}"
                
            xwnr_text += ans_line + "\r"
            idx += 1
            
        if doc.Bookmarks.Exists("wxnr"):
                rng = doc.Bookmarks("wxnr").Range
                rng.Text = xwnr_text
                rng.Font.Size = 12  # 小四号
                rng.ParagraphFormat.LineSpacingRule = 1  # wdLineSpace1pt5
                rng.ParagraphFormat.SpaceBefore = 0
                rng.ParagraphFormat.SpaceAfter = 0
                doc.Bookmarks.Add(Name="wxnr", Range=rng)
        
        # Signatures (删除被询问人签名区域，旧数据亦不渲染，仅保留询问人签名)
        sig_xwrqm = os.path.join(base_dir, "backend", "uploads", "signatures", f"{data.get('cbfbm')}_xwrqm.png")

        def _insert_sig(doc, bm_name, path):
            try:
                if path and os.path.exists(path):
                    if doc.Bookmarks.Exists(bm_name):
                        rng_sig = doc.Bookmarks(bm_name).Range
                        rng_sig.Collapse(1)
                        pic = rng_sig.InlineShapes.AddPicture(FileName=os.path.abspath(path), LinkToFile=False, SaveWithDocument=True)
                        pic.Width = 65
                        pic.Height = 26
            except Exception as pe:
                print(f"插入签名 {bm_name} 异常 (已安全忽略): {pe}")

        # 仅渲染询问人签名
        _insert_sig(doc, "xwrqm", sig_xwrqm)
        
        # 附带现场照片：在笔录末尾自动分页插入现场问询照片及图题
        photos = data.get("photos") or fd.get("photos") or []
        valid_photos = []
        for p_item in photos:
            raw_url = p_item if isinstance(p_item, str) else (p_item.get("url") or "")
            if not raw_url:
                continue
            clean_url = raw_url.strip()
            # 兼容多种 URL 表达形式
            if clean_url.startswith("/uploads/"):
                rel_path = clean_url.lstrip("/")
            elif "file=" in clean_url:
                rel_path = clean_url.split("file=")[-1].lstrip("/")
            else:
                rel_path = os.path.join("uploads", os.path.basename(clean_url))

            # 兼容各种工作目录层级
            candidates = [
                os.path.join(base_dir, "backend", rel_path),
                os.path.join(base_dir, rel_path),
                os.path.join(os.path.dirname(__file__), rel_path),
                os.path.abspath(clean_url)
            ]
            for cand in candidates:
                if os.path.exists(cand) and os.path.isfile(cand):
                    valid_photos.append(cand)
                    break

        if valid_photos:
            try:
                # 在文档末尾插入分页符 (wdPageBreak = 7)
                rng_end = doc.Content
                rng_end.Collapse(0)  # wdCollapseEnd = 0
                rng_end.InsertBreak(7)

                # 插入附图大标题
                p_title = doc.Paragraphs.Add()
                p_title.Range.Text = "附：现场问询核查照片\r"
                p_title.Range.Font.Name = "黑体"
                p_title.Range.Font.Size = 14
                p_title.Range.Font.Bold = True
                p_title.Range.ParagraphFormat.Alignment = 1  # 居中
                p_title.Range.ParagraphFormat.SpaceBefore = 12
                p_title.Range.ParagraphFormat.SpaceAfter = 14

                for p_idx, photo_abs_path in enumerate(valid_photos, 1):
                    # 插入照片
                    p_img = doc.Paragraphs.Add()
                    shape = p_img.Range.InlineShapes.AddPicture(
                        FileName=photo_abs_path,
                        LinkToFile=False,
                        SaveWithDocument=True
                    )
                    # 适度缩放照片宽度至标准 350 pt (~12.3 cm)，高宽比锁定
                    shape.Width = 350
                    shape.Height = shape.Height * (350.0 / max(shape.Width, 1))
                    p_img.Range.ParagraphFormat.Alignment = 1  # 居中
                    p_img.Range.ParagraphFormat.SpaceAfter = 6

                    # 插入图题说明
                    p_cap = doc.Paragraphs.Add()
                    p_cap.Range.Text = f"现场照片 {p_idx}\r"
                    p_cap.Range.Font.Name = "宋体"
                    p_cap.Range.Font.Size = 10.5
                    p_cap.Range.Font.Bold = False
                    p_cap.Range.ParagraphFormat.Alignment = 1  # 居中
                    p_cap.Range.ParagraphFormat.SpaceAfter = 16
            except Exception as pe:
                print(f"插入现场问询照片异常 (已忽略): {pe}")

        doc.SaveAs2(FileName=out_path, FileFormat=0)
        doc.Close(0)
        doc = None
        word.Quit()
        word = None
        return f"/api/download?file=downloads/{out_filename}"
    except Exception as e:
        print("export_waiye_inquiry error:", e)
        if doc:
            try: doc.Close(0)
            except: pass
        if word:
            try: word.Quit()
            except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()


def export_village_meeting_photos(township_name: str, village_name: str, photos: list, interviewees: list = None, shooting_date=None) -> str:
    """
    导出指定行政村的现场会与问询现场照片文档 (.docx)
    模板文件：附件/现场会照片.docx（座谈会影像记录表）
    命名格式：{township_name}{village_name}现场会照片.docx
    排版规范：
    - 基于《座谈会影像记录表》标准模板
    - 拍摄时间优先使用数据库中的 updated_at 时间
    - 自动替换核验行政区划、核验单位、拍摄时间
    - 在被访谈人姓名栏自动填充被访谈人名单
    - 在 2×2 网格中严格按照单元格大小自适应缩放照片尺寸，饱满居中排版，超过 4 张自动追加行
    """
    import os, copy, datetime, docx
    from PIL import Image, ImageOps
    from docx.shared import Cm, Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT

    try:
        from database import get_county_and_townships_sync
        county_info, _ = get_county_and_townships_sync()
        county_name = county_info.get("name", "全椒县")

        base_dir = get_base_dir()
        downloads_dir = os.path.join(base_dir, "backend", "downloads")
        os.makedirs(downloads_dir, exist_ok=True)

        clean_ts = sanitize_filename(township_name or "")
        clean_vn = sanitize_filename(village_name or "")
        loc_prefix = f"{clean_ts}{clean_vn}" if (clean_ts or clean_vn) else "现场会"
        out_filename = f"{loc_prefix}现场会照片.docx"
        out_path = os.path.join(downloads_dir, out_filename)

        tpl_path = os.path.join(base_dir, "附件", "现场会照片.docx")
        if not os.path.exists(tpl_path):
            tpl_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "附件", "现场会照片.docx")

        if os.path.exists(tpl_path):
            doc = docx.Document(tpl_path)
        else:
            doc = docx.Document()

        # 解析拍摄时间：优先使用数据库中记录的 updated_at 时间
        if shooting_date:
            if isinstance(shooting_date, (datetime.datetime, datetime.date)):
                now_date_str = f"{shooting_date.year}年{shooting_date.month:02d}月{shooting_date.day:02d}日"
            elif isinstance(shooting_date, str):
                clean_s = shooting_date.strip()
                try:
                    dt_parsed = datetime.datetime.fromisoformat(clean_s.replace("Z", "+00:00"))
                    now_date_str = f"{dt_parsed.year}年{dt_parsed.month:02d}月{dt_parsed.day:02d}日"
                except Exception:
                    now_date_str = clean_s
            else:
                now_dt = datetime.datetime.now()
                now_date_str = f"{now_dt.year}年{now_dt.month:02d}月{now_dt.day:02d}日"
        else:
            now_dt = datetime.datetime.now()
            now_date_str = f"{now_dt.year}年{now_dt.month:02d}月{now_dt.day:02d}日"

        loc_str = f"{county_name}{clean_ts}{clean_vn}" if (clean_ts or clean_vn) else county_name

        # 1. 替换或设置 P2 元数据段落
        meta_text = f"核验行政区划：{loc_str}    核验单位：{county_name}县级自查验收工作组    拍摄时间：{now_date_str}"
        if len(doc.paragraphs) > 1:
            p2 = doc.paragraphs[1]
            p2.text = meta_text
            if p2.runs:
                p2.runs[0].font.name = "黑体"
                p2.runs[0].font.bold = True
                p2.runs[0].font.size = Pt(11)
        else:
            p_title = doc.add_paragraph("座谈会影像记录表")
            p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p2 = doc.add_paragraph(meta_text)
            p2.alignment = WD_ALIGN_PARAGRAPH.CENTER

        # 2. 筛选有效照片
        valid_photos = []
        for p_item in (photos or []):
            raw_url = p_item if isinstance(p_item, str) else (p_item.get("url") or "")
            if not raw_url:
                continue
            clean_url = raw_url.strip()
            if clean_url.startswith("/uploads/"):
                rel_path = clean_url.lstrip("/")
            elif "file=" in clean_url:
                rel_path = clean_url.split("file=")[-1].lstrip("/")
            else:
                rel_path = os.path.join("uploads", os.path.basename(clean_url))

            candidates = [
                os.path.join(base_dir, "backend", rel_path),
                os.path.join(base_dir, rel_path),
                os.path.join(os.path.dirname(__file__), rel_path),
                os.path.abspath(clean_url)
            ]
            for cand in candidates:
                if os.path.exists(cand) and os.path.isfile(cand):
                    valid_photos.append(cand)
                    break

        # 3. 填充表格
        if doc.tables:
            table = doc.tables[0]

            # 填充第 1 行被访谈人姓名 (Row 0, Cell 1)
            names_str = "、".join(interviewees) if interviewees else ""
            cell_int = table.rows[0].cells[1]
            p_int = cell_int.paragraphs[0]
            p_int.text = names_str
            p_int.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if p_int.runs:
                p_int.runs[0].font.name = "仿宋"
                p_int.runs[0].font.size = Pt(11)

            # 照片插槽：Row 2 (cell 0, cell 2), Row 3 (cell 0, cell 2)
            # 若照片超过 4 张，按需增加行
            needed_photo_rows = max(2, (len(valid_photos) + 1) // 2)
            current_photo_rows = len(table.rows) - 2

            while current_photo_rows < needed_photo_rows:
                new_tr = copy.deepcopy(table.rows[3]._tr)
                for p in new_tr.xpath(".//w:p"):
                    p.getparent().remove(p)
                for tc in new_tr.xpath(".//w:tc"):
                    p_elem = docx.oxml.OxmlElement("w:p")
                    tc.append(p_elem)
                table._tbl.append(new_tr)
                current_photo_rows += 1

            if not valid_photos:
                p_empty = table.rows[2].cells[0].paragraphs[0]
                p_empty.text = "（注：当前行政村尚未上传现场会核查照片）"
                p_empty.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                for idx, p_path in enumerate(valid_photos):
                    row_idx = 2 + (idx // 2)
                    col_idx = 0 if (idx % 2 == 0) else 2
                    cell = table.rows[row_idx].cells[col_idx]
                    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    p_cell = cell.paragraphs[0]
                    p_cell.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_cell.paragraph_format.space_before = Pt(0)
                    p_cell.paragraph_format.space_after = Pt(0)
                    p_cell.paragraph_format.line_spacing = 1.0

                    try:
                        with Image.open(p_path) as im:
                            im = ImageOps.exif_transpose(im)
                            w, h = im.size

                        # 根据单元格实际物理尺寸（宽 7.5cm, 高 8.5cm）精确自适应缩放
                        # 扣除单元格内边距与段落安全余量：可用宽 7.12 cm，可用高 8.10 cm
                        max_w_cm = 7.12
                        max_h_cm = 8.10
                        scale = min(max_w_cm / w, max_h_cm / h)
                        target_w = Cm(w * scale)
                        target_h = Cm(h * scale)

                        run = p_cell.add_run()
                        run.add_picture(p_path, width=target_w, height=target_h)
                    except Exception as pe:
                        print(f"插入现场照片 {idx + 1} 异常: {pe}")
                        p_cell.text = "【照片加载失败】"
        else:
            # 容错：无表格时新建段落追加
            for p_idx, p_path in enumerate(valid_photos, 1):
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.add_run().add_picture(p_path, width=Cm(12.0))

        doc.save(out_path)
        return f"/api/download?file=downloads/{out_filename}"
    except Exception as e:
        print("export_village_meeting_photos error:", e)
        raise e


def export_sample_detail_excel(township_name: str, contractor_rows: list) -> str:
    """
    导出各乡镇自查抽样农户明细表 Excel 文件 (.xlsx)
    包含字段：序号、乡镇名、村名、组名、承包方编码、承包方名称、承包方证件号码。
    严格遵循 Excel 规范：居中对齐、文本自动换行、单元格全边框、数字与身份证文本格式防变形。
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    base_dir = get_base_dir()
    clean_ts = sanitize_filename(township_name)
    downloads_dir = os.path.join(base_dir, "backend", "downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    out_path = os.path.join(downloads_dir, f"自查抽样明细表_{clean_ts}.xlsx")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "抽样农户明细"
    ws.views.sheetView[0].showGridLines = True

    # 样式定义
    font_title = Font(name="微软雅黑", size=15, bold=True, color="1F497D")
    font_header = Font(name="微软雅黑", size=11, bold=True, color="FFFFFF")
    font_data = Font(name="微软雅黑", size=10)
    font_total = Font(name="微软雅黑", size=10, bold=True, color="000000")

    fill_header = PatternFill(start_color="2E75B6", end_color="2E75B6", fill_type="solid")
    fill_zebra = PatternFill(start_color="F2F5F9", end_color="F2F5F9", fill_type="solid")
    fill_total = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")

    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    thin_border_side = Side(border_style="thin", color="BFBFBF")
    double_border_side = Side(border_style="double", color="000000")
    border_all = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    border_total = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=double_border_side)

    # 1. 标题行
    ws.merge_cells("A1:G1")
    ws["A1"] = f"【{township_name}】二轮延包自查抽样农户明细表"
    ws["A1"].font = font_title
    ws["A1"].alignment = align_center
    ws.row_dimensions[1].height = 38

    # 2. 表头行
    headers = ["序号", "乡镇名", "村名", "组名", "承包方编码", "承包方名称", "承包方证件号码"]
    ws.append(headers)
    ws.row_dimensions[2].height = 26

    for col_idx in range(1, len(headers) + 1):
        c = ws.cell(row=2, column=col_idx)
        c.font = font_header
        c.fill = fill_header
        c.alignment = align_center
        c.border = border_all

    # 3. 填充数据行
    start_row = 3
    villages_set = set()
    groups_set = set()

    for i, r in enumerate(contractor_rows, 1):
        curr_row = start_row + i - 1
        ws.row_dimensions[curr_row].height = 22

        t_name = str(r.get("township_name") or township_name or "").strip()
        v_name = str(r.get("village_name") or "").strip()
        g_name = str(r.get("group_name") or "").strip()
        cbfbm = str(r.get("cbfbm") or "").strip()
        cbfmc = str(r.get("cbfmc") or "").strip()
        cbfzjhm = str(r.get("cbfzjhm") or "").strip()

        if v_name:
            villages_set.add(v_name)
        if g_name:
            groups_set.add((v_name, g_name))

        ws.append([i, t_name, v_name, g_name, cbfbm, cbfmc, cbfzjhm])

        is_zebra = (i % 2 == 0)
        row_fill = fill_zebra if is_zebra else None

        for c_idx in range(1, 8):
            cell = ws.cell(row=curr_row, column=c_idx)
            cell.font = font_data
            cell.alignment = align_center
            cell.border = border_all
            if row_fill:
                cell.fill = row_fill

        # 确保编码与身份证号码为严格文本格式防变形
        ws.cell(row=curr_row, column=5).number_format = "@"
        ws.cell(row=curr_row, column=7).number_format = "@"

    # 4. 统计汇总行
    total_row = start_row + len(contractor_rows)
    ws.row_dimensions[total_row].height = 26
    total_data = [
        "合计",
        township_name,
        f"共 {len(villages_set)} 个行政村",
        f"共 {len(groups_set)} 个组",
        f"总抽样: {len(contractor_rows)} 户",
        "-",
        "-"
    ]
    ws.append(total_data)

    for c_idx in range(1, 8):
        cell = ws.cell(row=total_row, column=c_idx)
        cell.font = font_total
        cell.fill = fill_total
        cell.alignment = align_center
        cell.border = border_total

    # 5. 列宽自适应
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            if cell.row == 1:
                continue
            val_str = str(cell.value or "")
            str_len = sum(2 if ord(char) > 127 else 1 for char in val_str)
            if str_len > max_len:
                max_len = str_len
        ws.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # 专门优化各列宽度
    ws.column_dimensions["A"].width = 8   # 序号
    ws.column_dimensions["B"].width = 14  # 乡镇名
    ws.column_dimensions["C"].width = 16  # 村名
    ws.column_dimensions["D"].width = 16  # 组名
    ws.column_dimensions["E"].width = 24  # 承包方编码 (18位)
    ws.column_dimensions["F"].width = 15  # 承包方名称
    ws.column_dimensions["G"].width = 24  # 承包方证件号码 (18位)

    wb.save(out_path)
    return f"/api/download?file=downloads/自查抽样明细表_{clean_ts}.xlsx"

