import os
import re
import shutil
import pythoncom
import win32com.client
from collections import defaultdict


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
    d_p6 = 5.0 if form_data.get('prog_6') else 0.0
    d_p7 = 5.0 if form_data.get('prog_7') else 0.0
    
    deduct_prog = min(d_p1 + d_p2 + d_p3 + d_p4 + d_p5 + d_p6 + d_p7, 30.0)
    score_prog = max(30.0 - deduct_prog, 0.0)
    
    # 3. 政策落实 (满分15)
    d_pol1 = min(len(form_data.get('policy_1', [])) * 1.0, 3.0)
    c_2_1 = float(form_data.get('policy_2_1', 0) or 0)
    c_2_2 = float(form_data.get('policy_2_2', 0) or 0)
    d_pol2 = min((c_2_1 + c_2_2) * 1.0, 3.0)
    
    c_3_1 = float(form_data.get('policy_3_1', 0) or 0)
    c_3_2 = float(form_data.get('policy_3_2', 0) or 0)
    d_pol3 = min((c_3_1 + c_3_2) * 1.0, 3.0)
    
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
    if any("未制定方案" in x for x in form_data.get("mech_1", [])):
        _cell_replace_checkbox(t1.Rows(2).Cells(4), "未制定方案")
    if any("直接套用上级方案" in x for x in form_data.get("mech_1", [])):
        _cell_replace_checkbox(t1.Rows(2).Cells(4), "直接套用上级方案")
    if any("分工不明确" in x for x in form_data.get("mech_1", [])):
        _cell_replace_checkbox(t1.Rows(2).Cells(4), "分工不明确")
    if any("制定程序不合法" in x for x in form_data.get("mech_1", [])):
        _cell_replace_checkbox(t1.Rows(2).Cells(4), "制定程序不合法")
    t1.Rows(2).Cells(6).Range.Text = f"{scores['deduct']['m1']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['m1'] > 0 else "0"
    
    # R3: 经费保障
    if any("支付不规范" in x for x in form_data.get("mech_2", [])):
        _cell_replace_checkbox(t1.Rows(3).Cells(4), "支付不规范")
    if any("支付不及时" in x for x in form_data.get("mech_2", [])):
        _cell_replace_checkbox(t1.Rows(3).Cells(4), "支付不及时")
    if any("经费没有县级兜底" in x for x in form_data.get("mech_2", [])):
        _cell_replace_checkbox(t1.Rows(3).Cells(4), "经费没有县级兜底")
    t1.Rows(3).Cells(6).Range.Text = f"{scores['deduct']['m2']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['m2'] > 0 else "0"

    # R4: 宣传
    if any("没有宣传材料" in x for x in form_data.get("mech_3", [])):
        _cell_replace_checkbox(t1.Rows(4).Cells(4), "没有宣传材料")
    t1.Rows(4).Cells(6).Range.Text = f"{scores['deduct']['m3']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['m3'] > 0 else "0"

    # R5: 培训
    if any("没有培训材料" in x for x in form_data.get("mech_4", [])):
        _cell_replace_checkbox(t1.Rows(5).Cells(4), "没有培训材料")
    if any("没有分批次培训" in x for x in form_data.get("mech_4", [])):
        _cell_replace_checkbox(t1.Rows(5).Cells(4), "没有分批次培训")
    if any("培训材料不齐全" in x for x in form_data.get("mech_4", [])):
        _cell_replace_checkbox(t1.Rows(5).Cells(4), "培训材料不齐全")
    if any("培训未覆盖县乡村组" in x for x in form_data.get("mech_4", [])):
        _cell_replace_checkbox(t1.Rows(5).Cells(4), "培训未覆盖县乡村组")
    t1.Rows(5).Cells(6).Range.Text = f"{scores['deduct']['m4']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['m4'] > 0 else "0"

    # R6: 总计扣分
    t1.Rows(6).Cells(3).Range.Text = f"{scores['deduct']['mech']:.1f}".rstrip('0').rstrip('.')
    
    # R7: 重要问题描述
    issues = []
    if form_data.get("mech_1"): issues.extend(form_data.get("mech_1", []))
    if form_data.get("mech_2"): issues.extend(form_data.get("mech_2", []))
    if form_data.get("mech_3"): issues.extend(form_data.get("mech_3", []))
    if form_data.get("mech_4"): issues.extend(form_data.get("mech_4", []))
    _set_issues_cell(t1.Rows(7).Cells(2), issues) 

def fill_table_2(t2, form_data, scores):
    # R2: 成立机构
    if any("未召开会议" in x for x in form_data.get("prog_1", [])):
        _cell_replace_checkbox(t2.Rows(2).Cells(4), "未召开会议")
    if any("未公示工作组名单" in x for x in form_data.get("prog_1", [])):
        _cell_replace_checkbox(t2.Rows(2).Cells(4), "未公示工作组名单")
    if any("公示时间不足15天" in x for x in form_data.get("prog_1", [])):
        _cell_replace_checkbox(t2.Rows(2).Cells(4), "公示时间不足15天")
    if any("参会人数不足法定数量" in x for x in form_data.get("prog_1", [])):
        _cell_replace_checkbox(t2.Rows(2).Cells(4), "参会人数不足法定数量")
    t2.Rows(2).Cells(6).Range.Text = f"{scores['deduct']['p1']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p1'] > 0 else "0"

    # R3: 摸底核实
    if any("没有进行摸底" in x for x in form_data.get("prog_2", [])):
        _cell_replace_checkbox(t2.Rows(3).Cells(4), "没有进行摸底")
    if any("摸底表农户未签署" in x for x in form_data.get("prog_2", [])):
        _cell_replace_checkbox(t2.Rows(3).Cells(4), "摸底表农户未签署")
    if any("摸底表中没有表达延包意愿" in x for x in form_data.get("prog_2", [])):
        _cell_replace_checkbox(t2.Rows(3).Cells(4), "摸底表中没有表达延包意愿")
    if any("摸底表其它签署不齐全" in x for x in form_data.get("prog_2", [])):
        _cell_replace_checkbox(t2.Rows(3).Cells(4), "摸底表其它签署不齐全")
    if any("特殊人员摸底不清或未统计" in x for x in form_data.get("prog_2", [])):
        _cell_replace_checkbox(t2.Rows(3).Cells(4), "特殊人员摸底不清或未统计")
    if any("户变化未统计" in x for x in form_data.get("prog_2", [])):
        _cell_replace_checkbox(t2.Rows(3).Cells(4), "户变化未统计")
    if any("矛盾纠纷未登记或处理不当" in x for x in form_data.get("prog_2", [])):
        _cell_replace_checkbox(t2.Rows(3).Cells(4), "矛盾纠纷未登记或处理不当")
    if any("承包地变化未摸清" in x for x in form_data.get("prog_2", [])):
        _cell_replace_checkbox(t2.Rows(3).Cells(4), "承包地变化未摸清")
    if any("没有应确尽确" in x for x in form_data.get("prog_2", [])):
        _cell_replace_checkbox(t2.Rows(3).Cells(4), "没有应确尽确")
    t2.Rows(3).Cells(6).Range.Text = f"{scores['deduct']['p2']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p2'] > 0 else "0"

    # R4: 制定方案
    if any("没有延包方案" in x for x in form_data.get("prog_3", [])):
        _cell_replace_checkbox(t2.Rows(4).Cells(4), "没有延包方案")
    if any("延包方案未上报" in x for x in form_data.get("prog_3", [])):
        _cell_replace_checkbox(t2.Rows(4).Cells(4), "延包方案未上报")
    if any("延包方案未公示" in x for x in form_data.get("prog_3", [])):
        _cell_replace_checkbox(t2.Rows(4).Cells(4), "延包方案未公示")
    if any("未召开会议讨论延包方案" in x for x in form_data.get("prog_3", [])):
        _cell_replace_checkbox(t2.Rows(4).Cells(4), "未召开会议讨论延包方案")
    t2.Rows(4).Cells(6).Range.Text = f"{scores['deduct']['p3']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p3'] > 0 else "0"

    # R5: 调查公示
    if any("没有公示材料" in x for x in form_data.get("prog_4", [])):
        _cell_replace_checkbox(t2.Rows(5).Cells(4), "没有公示材料")
    if any("没有公示不足15天" in x for x in form_data.get("prog_4", [])):
        _cell_replace_checkbox(t2.Rows(5).Cells(4), "没有公示不足15天")
    if any("公示结果未确认" in x for x in form_data.get("prog_4", [])):
        _cell_replace_checkbox(t2.Rows(5).Cells(4), "公示结果未确认")
    if any("各类资料不齐全" in x for x in form_data.get("prog_4", [])):
        _cell_replace_checkbox(t2.Rows(5).Cells(4), "各类资料不齐全")
    if any("各类资料制作粗糙" in x for x in form_data.get("prog_4", [])):
        _cell_replace_checkbox(t2.Rows(5).Cells(4), "各类资料制作粗糙")
    if any("各类资料签署不规范" in x for x in form_data.get("prog_4", [])):
        _cell_replace_checkbox(t2.Rows(5).Cells(4), "各类资料签署不规范")
    if any("权属证明材料不齐全" in x for x in form_data.get("prog_4", [])):
        _cell_replace_checkbox(t2.Rows(5).Cells(4), "权属证明材料不齐全")
    if any("其它证明材料不齐全" in x for x in form_data.get("prog_4", [])):
        _cell_replace_checkbox(t2.Rows(5).Cells(4), "其它证明材料不齐全")
    t2.Rows(5).Cells(6).Range.Text = f"{scores['deduct']['p4']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p4'] > 0 else "0"

    # R6: 签订合同
    if any("合同版本格式不正确" in x for x in form_data.get("prog_5", [])):
        _cell_replace_checkbox(t2.Rows(6).Cells(4), "合同版本格式不正确")
    if any("合同网签率未达到95%" in x for x in form_data.get("prog_5", [])):
        _cell_replace_checkbox(t2.Rows(6).Cells(4), "合同网签率未达到95%")
    if any("没有地块示意图" in x for x in form_data.get("prog_5", [])):
        _cell_replace_checkbox(t2.Rows(6).Cells(4), "没有地块示意图")
    t2.Rows(6).Cells(6).Range.Text = f"{scores['deduct']['p5']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p5'] > 0 else "0"

    # R7: 完善证书
    if any("未进行信息共享" in x for x in form_data.get("prog_6", [])):
        _cell_replace_checkbox(t2.Rows(7).Cells(4), "未进行信息共享")
    if any("未与不动产登记部门有序衔接" in x for x in form_data.get("prog_6", [])):
        _cell_replace_checkbox(t2.Rows(7).Cells(4), "未与不动产登记部门有序衔接")
    t2.Rows(7).Cells(6).Range.Text = f"{scores['deduct']['p6']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p6'] > 0 else "0"

    # R8: 资料归档
    if any("档案整理第三方无涉密档案整理资质" in x for x in form_data.get("prog_7", [])):
        _cell_replace_checkbox(t2.Rows(8).Cells(4), "档案整理第三方无涉密档案整理资质")
    if any("没有进行档案验收" in x for x in form_data.get("prog_7", [])):
        _cell_replace_checkbox(t2.Rows(8).Cells(4), "没有进行档案验收")
    if any("档案验收不符合相关标准" in x for x in form_data.get("prog_7", [])):
        _cell_replace_checkbox(t2.Rows(8).Cells(4), "档案验收不符合相关标准")
    t2.Rows(8).Cells(6).Range.Text = f"{scores['deduct']['p7']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p7'] > 0 else "0"

    # R9: 总计扣分
    t2.Rows(9).Cells(3).Range.Text = f"{scores['deduct']['prog']:.1f}".rstrip('0').rstrip('.')
    
    # R10: 重要问题描述
    issues = []
    if form_data.get("prog_1"): issues.extend(form_data.get("prog_1", []))
    if form_data.get("prog_2"): issues.extend(form_data.get("prog_2", []))
    if form_data.get("prog_3"): issues.extend(form_data.get("prog_3", []))
    if form_data.get("prog_4"): issues.extend(form_data.get("prog_4", []))
    if form_data.get("prog_5"): issues.extend(form_data.get("prog_5", []))
    if form_data.get("prog_6"): issues.extend(form_data.get("prog_6", []))
    if form_data.get("prog_7"): issues.extend(form_data.get("prog_7", []))
    _set_issues_cell(t2.Rows(10).Cells(2), issues) 

def fill_table_3(t3, form_data, scores):
    # R2: 大稳定、小调整
    if any("小调整比率过大或手续不齐全" in x for x in form_data.get("policy_1", [])):
        _cell_replace_checkbox(t3.Rows(2).Cells(4), "小调整比率过大或手续不齐全")
    if any("打乱重分" in x for x in form_data.get("policy_1", [])):
        _cell_replace_checkbox(t3.Rows(2).Cells(4), "打乱重分")
    if any("违法调整或收回承包地" in x for x in form_data.get("policy_1", [])):
        _cell_replace_checkbox(t3.Rows(2).Cells(4), "违法调整或收回承包地")
    t3.Rows(2).Cells(6).Range.Text = f"{scores['deduct']['pol1']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol1'] > 0 else "0"

    # R3: 保障土地承包权益 (带数量)
    c_2_1 = int(form_data.get("policy_2_1", 0) or 0)
    c_2_2 = int(form_data.get("policy_2_2", 0) or 0)
    if c_2_1 > 0:
        _cell_replace_checkbox(t3.Rows(3).Cells(4), "未保障特殊群体权益")
        # also append count - use find/replace for the full text
        rng3 = t3.Rows(3).Cells(4).Range
        f3 = rng3.Find; f3.ClearFormatting(); f3.Replacement.ClearFormatting()
        f3.Execute(FindText="未保障特殊群体权益", ReplaceWith=f"未保障特殊群体权益（{c_2_1}起）", Replace=2, MatchCase=True)
    if c_2_2 > 0:
        _cell_replace_checkbox(t3.Rows(3).Cells(4), "未保障无地户权益")
        rng3b = t3.Rows(3).Cells(4).Range
        f3b = rng3b.Find; f3b.ClearFormatting(); f3b.Replacement.ClearFormatting()
        f3b.Execute(FindText="未保障无地户权益", ReplaceWith=f"未保障无地户权益（{c_2_2}起）", Replace=2, MatchCase=True)
    t3.Rows(3).Cells(6).Range.Text = f"{scores['deduct']['pol2']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol2'] > 0 else "0"

    # R4: 依法收回消亡户承包地 (带数量)
    c_3_1 = int(form_data.get("policy_3_1", 0) or 0)
    c_3_2 = int(form_data.get("policy_3_2", 0) or 0)
    if c_3_1 > 0:
        _cell_replace_checkbox(t3.Rows(4).Cells(4), "没有应收尽收")
        rng4 = t3.Rows(4).Cells(4).Range
        f4 = rng4.Find; f4.ClearFormatting(); f4.Replacement.ClearFormatting()
        f4.Execute(FindText="没有应收尽收", ReplaceWith=f"没有应收尽收（{c_3_1}起）", Replace=2, MatchCase=True)
    if c_3_2 > 0:
        _cell_replace_checkbox(t3.Rows(4).Cells(4), "采用不正当方式隐匿消亡户")
        rng4b = t3.Rows(4).Cells(4).Range
        f4b = rng4b.Find; f4b.ClearFormatting(); f4b.Replacement.ClearFormatting()
        f4b.Execute(FindText="采用不正当方式隐匿消亡户", ReplaceWith=f"采用不正当方式隐匿消亡户（{c_3_2}起）", Replace=2, MatchCase=True)
    t3.Rows(4).Cells(6).Range.Text = f"{scores['deduct']['pol3']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol3'] > 0 else "0"

    # R5: 严格机动地和新增耕地管理
    if any("机动地、新增耕地处置不当" in x for x in form_data.get("policy_4", [])):
        _cell_replace_checkbox(t3.Rows(5).Cells(4), "机动地、新增耕地处置不当")
    if any("机动地比率过高" in x for x in form_data.get("policy_4", [])):
        _cell_replace_checkbox(t3.Rows(5).Cells(4), "机动地比率过高")
    t3.Rows(5).Cells(6).Range.Text = f"{scores['deduct']['pol4']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol4'] > 0 else "0"

    # R6: 从严掌握确权确股不确地
    if any("违背农户意愿强行推进" in x for x in form_data.get("policy_5", [])):
        _cell_replace_checkbox(t3.Rows(6).Cells(4), "违背农户意愿强行推进")
    if any("确权确股不确地手续不齐全" in x for x in form_data.get("policy_5", [])):
        _cell_replace_checkbox(t3.Rows(6).Cells(4), "确权确股不确地手续不齐全")
    t3.Rows(6).Cells(6).Range.Text = f"{scores['deduct']['pol5']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol5'] > 0 else "0"

    # R7: 总计扣分
    t3.Rows(7).Cells(3).Range.Text = f"{scores['deduct']['policy']:.1f}".rstrip('0').rstrip('.')
    
    # R8: 重要问题描述
    issues = []
    if form_data.get("policy_1"): issues.extend(form_data.get("policy_1", []))
    if c_2_1 > 0: issues.append(f"未保障特殊群体权益（{c_2_1}起）")
    if c_2_2 > 0: issues.append(f"未保障无地户权益（{c_2_2}起）")
    if c_3_1 > 0: issues.append(f"消亡户未应收尽收（{c_3_1}起）")
    if c_3_2 > 0: issues.append(f"不正当方式隐匿消亡户（{c_3_2}起）")
    if form_data.get("policy_4"): issues.extend(form_data.get("policy_4", []))
    if form_data.get("policy_5"): issues.extend(form_data.get("policy_5", []))
    _set_issues_cell(t3.Rows(8).Cells(2), issues) 

def fill_table_4(t4, form_data, scores):
    # R2: 加强风险防范
    if any("未建立矛盾纠纷处置机制" in x for x in form_data.get("effect_1", [])):
        _cell_replace_checkbox(t4.Rows(2).Cells(4), "未建立矛盾纠纷处置机制")
    if any("未建立舆情处置办法" in x for x in form_data.get("effect_1", [])):
        _cell_replace_checkbox(t4.Rows(2).Cells(4), "未建立舆情处置办法")
    if any("没有矛盾纠纷处理台账" in x for x in form_data.get("effect_1", [])):
        _cell_replace_checkbox(t4.Rows(2).Cells(4), "没有矛盾纠纷处理台账")
    t4.Rows(2).Cells(6).Range.Text = f"{scores['deduct']['effect']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['effect'] > 0 else "0"

    # R3: 总计扣分
    t4.Rows(3).Cells(3).Range.Text = f"{scores['deduct']['effect']:.1f}".rstrip('0').rstrip('.')
    
    # R4: 重要问题描述
    issues = []
    if form_data.get("effect_1"): issues.extend(form_data.get("effect_1", []))
    _set_issues_cell(t4.Rows(4).Cells(2), issues) 

def export_neiye_att6_township(township_name, form_data):
    pythoncom.CoInitialize()
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        
        base_dir = os.path.abspath(r"G:\全椒县二轮延包\全椒县县级验收管理平台")
        tpl = os.path.join(base_dir, "附件", "附件6.doc")
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_path = os.path.join(base_dir, "backend", "downloads", f"附件6_全椒县县级自查内业组检查记录表_{township_name}.doc")
        shutil.copy(tpl, out_path)
        
        doc = word.Documents.Open(out_path)
        
        # Fill 行政区划名称 bookmarks in all 4 pages (xzqh_1 ~ xzqh_4)
        _xzqh_text = "全椒县" + township_name
        _fill_bookmarks(doc, ["xzqh_1", "xzqh_2", "xzqh_3", "xzqh_4"], _xzqh_text)
        
        scores = calculate_neiye_subscores(form_data)
        
        fill_table_1(doc.Tables(1), form_data, scores)
        fill_table_2(doc.Tables(2), form_data, scores)
        fill_table_3(doc.Tables(3), form_data, scores)
        fill_table_4(doc.Tables(4), form_data, scores)
        
        doc.Save()
        doc.Close(False)
        word.Quit()
        return f"/api/download?file=downloads/附件6_全椒县县级自查内业组检查记录表_{township_name}.doc"
    except Exception as e:
        print("export_neiye_att6_township error:", e)
        try: word.Quit()
        except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()

def export_neiye_att6_county(form_data):
    pythoncom.CoInitialize()
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        
        base_dir = os.path.abspath(r"G:\全椒县二轮延包\全椒县县级验收管理平台")
        tpl = os.path.join(base_dir, "附件", "附件6.doc")
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_path = os.path.join(base_dir, "backend", "downloads", "附件6_全椒县县级自查内业组检查记录表（1_4）.doc")
        shutil.copy(tpl, out_path)
        
        doc = word.Documents.Open(out_path)
        
        # Fill 行政区划名称 bookmark for page 1 only (county export)
        _fill_bookmarks(doc, ["xzqh_1"], "全椒县")
        
        scores = calculate_neiye_subscores(form_data)
        fill_table_1(doc.Tables(1), form_data, scores)
        
        # Delete Table 4, 3, 2 in reverse order
        while doc.Tables.Count > 1:
            doc.Tables(doc.Tables.Count).Delete()
        
        # Trim paragraphs after Table 1
        end_pos = doc.Content.End
        for p in doc.Paragraphs:
            if "复核者：" in p.Range.Text:
                end_pos = p.Range.End
                break
        if end_pos < doc.Content.End:
            rng = doc.Range(end_pos, doc.Content.End)
            rng.Delete()
        
        doc.Save()
        doc.Close(False)
        word.Quit()
        return "/api/download?file=downloads/附件6_全椒县县级自查内业组检查记录表（1_4）.doc"
    except Exception as e:
        print("export_neiye_att6_county error:", e)
        try: word.Quit()
        except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()

def export_neiye_att7(records_by_qsdwdm):
    pythoncom.CoInitialize()
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False
        
        base_dir = os.path.abspath(r"G:\全椒县二轮延包\全椒县县级验收管理平台")
        tpl = os.path.join(base_dir, "附件", "附件7.doc")
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_path = os.path.join(base_dir, "backend", "downloads", "附件7_全椒县县级自查内业组检查得分表.doc")
        shutil.copy(tpl, out_path)
        
        doc = word.Documents.Open(out_path)
        t = doc.Tables(1)
        
        # 1. County row (Row 2)
        
        
        county_rec = records_by_qsdwdm.get("341124")
        if county_rec:
            c_scores = calculate_neiye_subscores(county_rec.get("form_data", {}))
            county_mech = c_scores['score']['mech']
        else:
            county_mech = 15.0

        t.Rows(2).Cells(1).Range.Text = "1"
        t.Rows(2).Cells(2).Range.Text = "全椒县"
        t.Rows(2).Cells(3).Range.Text = f"{county_mech:.1f}".rstrip('0').rstrip('.')
        t.Rows(2).Cells(4).Range.Text = "/"
        t.Rows(2).Cells(5).Range.Text = "/"
        t.Rows(2).Cells(6).Range.Text = "/"
        t.Rows(2).Cells(7).Range.Text = "/"

        township_list = [
            ("341124100", "襄河镇"),
            ("341124101", "古河镇"),
            ("341124102", "大墅镇"),
            ("341124103", "二郎口镇"),
            ("341124104", "武岗镇"),
            ("341124105", "马厂镇"),
            ("341124106", "石沛镇"),
            ("341124107", "十字镇"),
            ("341124108", "西王镇"),
            ("341124109", "六镇镇")
        ]
        
        sums = {"mech": 0.0, "prog": 0.0, "policy": 0.0, "effect": 0.0, "total": 0.0}
        count_evaluated = 0
        
        for idx, (code, name) in enumerate(township_list):
            r_idx = idx + 3
            t.Rows(r_idx).Cells(1).Range.Text = str(idx + 2)
            t.Rows(r_idx).Cells(2).Range.Text = name
            
            rec = records_by_qsdwdm.get(code)
            if rec:
                count_evaluated += 1
                sc = calculate_neiye_subscores(rec.get("form_data", {}))["score"]
                t.Rows(r_idx).Cells(3).Range.Text = f"{sc['mech']:.1f}".rstrip('0').rstrip('.')
                t.Rows(r_idx).Cells(4).Range.Text = f"{sc['prog']:.1f}".rstrip('0').rstrip('.')
                t.Rows(r_idx).Cells(5).Range.Text = f"{sc['policy']:.1f}".rstrip('0').rstrip('.')
                t.Rows(r_idx).Cells(6).Range.Text = f"{sc['effect']:.1f}".rstrip('0').rstrip('.')
                t.Rows(r_idx).Cells(7).Range.Text = f"{sc['total']:.1f}".rstrip('0').rstrip('.')
                
                for k in sums: sums[k] += sc[k]
            else:
                t.Rows(r_idx).Cells(3).Range.Text = ""
                t.Rows(r_idx).Cells(4).Range.Text = ""
                t.Rows(r_idx).Cells(5).Range.Text = ""
                t.Rows(r_idx).Cells(6).Range.Text = ""
                t.Rows(r_idx).Cells(7).Range.Text = ""

        # Row 13: 总评 (平均分)
        t.Rows(13).Cells(1).Range.Text = "12"
        t.Rows(13).Cells(2).Range.Text = "总评"
        if count_evaluated > 0:
            mech_count = count_evaluated + 1
            avg_mech = (sums['mech'] + county_mech) / mech_count
            avg_prog = sums['prog'] / count_evaluated
            avg_policy = sums['policy'] / count_evaluated
            avg_effect = sums['effect'] / count_evaluated
            avg_total = avg_mech + avg_prog + avg_policy + avg_effect
            
            t.Rows(13).Cells(3).Range.Text = f"{avg_mech:.1f}"
            t.Rows(13).Cells(4).Range.Text = f"{avg_prog:.1f}"
            t.Rows(13).Cells(5).Range.Text = f"{avg_policy:.1f}"
            t.Rows(13).Cells(6).Range.Text = f"{avg_effect:.1f}"
            t.Rows(13).Cells(7).Range.Text = f"{avg_total:.1f}"
        else:
            t.Rows(13).Cells(3).Range.Text = ""
            t.Rows(13).Cells(4).Range.Text = ""
            t.Rows(13).Cells(5).Range.Text = ""
            t.Rows(13).Cells(6).Range.Text = ""
            t.Rows(13).Cells(7).Range.Text = ""



        doc.Save()
        doc.Close(False)
        word.Quit()
        return "/api/download?file=downloads/附件7_全椒县县级自查内业组检查得分表.doc"
    except Exception as e:
        print("export_neiye_att7 error:", e)
        try: word.Quit()
        except: pass
        raise e
    finally:
        pythoncom.CoUninitialize()
def export_att4(township_name):
    base_dir = os.path.abspath(r"G:\全椒县二轮延包\全椒县县级验收管理平台")
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
        
        base_dir = os.path.abspath(r"G:\全椒县二轮延包\全椒县县级验收管理平台")
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
        
        base_dir = os.path.abspath(r"G:\全椒县二轮延包\全椒县县级验收管理平台")
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
        rng.Text = f"   乡镇：{township_name} \t行政村：{village_name} \t村民小组：{group_name}" + " "*30 + "2026 年    月    日"
        
        t8 = doc8.Tables(1)
        for _ in range(5):
            try: t8.Rows(3).Delete()
            except: pass
            
        for _ in range(max(0, len(group_rows) - 1)):
            t8.Rows(2).Select()
            word.Selection.InsertRowsBelow(1)
            
        total_errors = 0
        satisfaction_count = 0
        
        # Group by contractor to calculate unique contractor-level errors and satisfaction
        processed_contractors = set()
        contractor_count = 0

        for i, r in enumerate(group_rows):
            r_idx = i + 2
            farmer_name = r.get('cbfmc', '') or r.get('承包方代表', '')
            cbfbm = str(r.get("cbfbm", "") or r.get("cbfbm_short", "") or r.get("cbfmc", ""))
            
            # Parcel-level errors
            for k in ['area_acknowledged', 'bound_correct', 'self_verified']:
                if r.get(k) == 'X':
                    total_errors += 1
            
            # Contractor-level errors & satisfaction
            sat = r.get('satisfaction', '满意')
            if cbfbm not in processed_contractors:
                processed_contractors.add(cbfbm)
                contractor_count += 1
                for k in ['rights_correct', 'member_qualified', 'self_signed', 'phone_correct']:
                    if r.get(k) == 'X':
                        total_errors += 1
                if sat == '满意':
                    satisfaction_count += 1
                
            t8.Cell(r_idx, 1).Range.Text = str(i + 1)
            t8.Cell(r_idx, 2).Range.Text = farmer_name
            t8.Cell(r_idx, 3).Range.Text = str(r.get('cbfbm_short', '') or r.get('承包方编码(缩略码)', ''))
            
            lxdh_val = str(r.get('lxdh', '') or r.get('联系电话', ''))
            if r.get('phone_correct') == 'X':
                t8.Cell(r_idx, 4).Range.Text = lxdh_val + " (X)" if lxdh_val else "X"
            else:
                t8.Cell(r_idx, 4).Range.Text = lxdh_val

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
        effect_score = (satisfaction_count / contractor_count * 10.0) if contractor_count > 0 else 10.0
        
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
                for col_idx in [16, 15, 14, 13, 11, 9, 4, 3, 2]:
                    t8.Cell(r_start, col_idx).Merge(t8.Cell(r_end, col_idx))
                cell_target = t8.Cell(r_start, 16)
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

# ================= 自查整改（附件12 / 附件13） =================

WAIYE_FLAG_LABELS = [
    ("area_acknowledged", "面积未确认"),
    ("rights_correct", "权利不正确"),
    ("bound_correct", "边界不正确"),
    ("member_qualified", "成员不合规"),
    ("self_verified", "未自验"),
    ("self_signed", "未自签"),
]

def _build_rectify_rows(neiye_form, waiye_rows, township_name):
    rows = []
    # 内业问题
    if isinstance(neiye_form, dict):
        for key, val in neiye_form.items():
            if isinstance(val, list):
                for item in val:
                    if item:
                        rows.append({
                            "source": "内业",
                            "level": "一般",
                            "desc": f"{township_name} {str(item)}",
                            "scope": "",
                            "unit": township_name,
                        })
    # 外业问题：waiye_samples 中标记为 X 的检查项
    for r in (waiye_rows or []):
        failed = [lbl for key, lbl in WAIYE_FLAG_LABELS if str(r.get(key, "")).strip() == "X"]
        if failed:
            loc = f"{township_name}{r.get('village_name', '')}{r.get('group_name', '')} {r.get('cbfmc', '')}".strip()
            rows.append({
                "source": "外业",
                "level": "一般",
                "desc": f"{loc}：{chr(0x3001).join(failed)}",
                "scope": "",
                "unit": r.get('village_name', township_name),
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

        base_dir = os.path.abspath(r"G:\全椒县二轮延包\全椒县县级验收管理平台")
        tpl = os.path.join(base_dir, "附件", "附件12.doc")
        clean_ts = sanitize_filename(township_name)
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_path = os.path.join(base_dir, "backend", "downloads", f"附件12_整改通知书_{clean_ts}.doc")
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        shutil.copy(tpl, out_path)

        doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)

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

        base_dir = os.path.abspath(r"G:\全椒县二轮延包\全椒县县级验收管理平台")
        tpl = os.path.join(base_dir, "附件", "附件13.doc")
        clean_ts = sanitize_filename(township_name)
        os.makedirs(os.path.join(base_dir, "backend", "downloads"), exist_ok=True)
        out_path = os.path.join(base_dir, "backend", "downloads", f"附件13_问题整改销号台账_{clean_ts}.doc")
        if os.path.exists(out_path):
            try: os.remove(out_path)
            except: pass
        shutil.copy(tpl, out_path)

        doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
        t = doc.Tables(1)

        # 删除模板中的空白数据行，仅保留表头
        while t.Rows.Count > 1:
            t.Rows(t.Rows.Count).Delete()

        data_rows = _build_rectify_rows(neiye_form, waiye_rows, township_name)

        for i, item in enumerate(data_rows):
            if i == 0:
                t.Rows(1).Select()
                word.Selection.InsertRowsBelow(1)
            else:
                t.Rows(t.Rows.Count).Select()
                word.Selection.InsertRowsBelow(1)
            r = i + 2
            t.Cell(r, 1).Range.Text = str(i + 1)                        # 序号
            t.Cell(r, 2).Range.Text = item["source"]                   # 问题来源: 内业/外业/专家组
            t.Cell(r, 3).Range.Text = item.get("level", "一般")        # 问题等级: 一般/较重/重大
            t.Cell(r, 4).Range.Text = item["desc"]                     # 问题具体描述
            t.Cell(r, 5).Range.Text = item.get("scope", "")            # 涉及资料/农户数量
            t.Cell(r, 6).Range.Text = item.get("unit", "")             # 整改责任单位: 乡镇/村
            t.Cell(r, 7).Range.Text = ""                               # 责任领导
            t.Cell(r, 8).Range.Text = ""                               # 责任人
            t.Cell(r, 9).Range.Text = "对照问题逐项整改，补齐材料，规范程序"  # 整改措施
            t.Cell(r, 10).Range.Text = ""                              # 计划完成时限
            t.Cell(r, 11).Range.Text = ""                              # 实际完成时间
            t.Cell(r, 12).Range.Text = ""                              # 佐证材料名称
            t.Cell(r, 13).Range.Text = "通过"                              # 复核情况: 通过/不通过
            t.Cell(r, 14).Range.Text = ""                              # 复核人签字
            t.Cell(r, 15).Range.Text = "未销号"                        # 销号状态: 已销号/未销号
            t.Cell(r, 16).Range.Text = ""                              # 备注

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
