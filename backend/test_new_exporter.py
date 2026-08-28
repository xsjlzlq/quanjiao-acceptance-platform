import os
import shutil
import pythoncom
import win32com.client
from collections import defaultdict

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
    txt = t1.Rows(2).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    for opt in ["未制定方案", "直接套用上级方案", "分工不明确", "制定程序不合法"]:
        if any(opt in x for x in form_data.get("mech_1", [])):
            txt = txt.replace(f"□{opt}", f"☑{opt}")
    t1.Rows(2).Cells(4).Range.Text = txt
    t1.Rows(2).Cells(6).Range.Text = f"{scores['deduct']['m1']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['m1'] > 0 else "0"
    
    # R3: 经费保障
    txt = t1.Rows(3).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    if any("支付不规范" in x for x in form_data.get("mech_2", [])):
        txt = txt.replace("□支付不规范", "☑支付不规范")
    if any("支付不及时" in x for x in form_data.get("mech_2", [])):
        txt = txt.replace("□支付不及时", "☑支付不及时")
    if any("兜底" in x for x in form_data.get("mech_2", [])):
        txt = txt.replace("□经费没有县级兜底", "☑经费没有县级兜底")
    t1.Rows(3).Cells(4).Range.Text = txt
    t1.Rows(3).Cells(6).Range.Text = f"{scores['deduct']['m2']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['m2'] > 0 else "0"

    # R4: 宣传
    txt = t1.Rows(4).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    if form_data.get("mech_3"):
        txt = txt.replace("□没有宣传材料", "☑没有宣传材料")
    t1.Rows(4).Cells(4).Range.Text = txt
    t1.Rows(4).Cells(6).Range.Text = f"{scores['deduct']['m3']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['m3'] > 0 else "0"

    # R5: 培训
    txt = t1.Rows(5).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    m4_list = form_data.get("mech_4", [])
    if isinstance(m4_list, list):
        for opt in ["没有培训材料", "没有分批次培训", "培训材料不齐全", "培训未覆盖县乡村组"]:
            short = opt.replace("县", "")
            if any(opt in x or short in x for x in m4_list):
                txt = txt.replace(f"□{opt}", f"☑{opt}")
    t1.Rows(5).Cells(4).Range.Text = txt
    t1.Rows(5).Cells(6).Range.Text = f"{scores['deduct']['m4']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['m4'] > 0 else "0"

    # R6: 总计扣分
    t1.Rows(6).Cells(3).Range.Text = f"{scores['deduct']['mech']:.1f}".rstrip('0').rstrip('.')
    
    # R7: 重要问题描述
    issues = []
    if form_data.get("mech_1"): issues.append("延包方案与分工存在问题：" + "、".join(form_data.get("mech_1", [])))
    if form_data.get("mech_2"): issues.append("经费保障存在问题：" + "、".join(form_data.get("mech_2", [])))
    if form_data.get("mech_3"): issues.append("宣传存在问题：" + "、".join(form_data.get("mech_3", [])))
    if form_data.get("mech_4"): issues.append("培训存在问题：" + "、".join(form_data.get("mech_4", [])))
    t1.Rows(7).Cells(2).Range.Text = "\n".join(issues) if issues else "无"

def fill_table_2(t2, form_data, scores):
    # R2: 成立机构
    txt = t2.Rows(2).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    for opt in ["未召开会议", "未公示工作组名单", "公示时间不足15天", "参会人数不足法定数量"]:
        short = opt.replace("工作组", "").replace("时间", "").replace("数量", "")
        if any(opt in x or short in x for x in form_data.get("prog_1", [])):
            txt = txt.replace(f"□{opt}", f"☑{opt}")
    t2.Rows(2).Cells(4).Range.Text = txt
    t2.Rows(2).Cells(6).Range.Text = f"{scores['deduct']['p1']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p1'] > 0 else "0"

    # R3: 摸底核实
    txt = t2.Rows(3).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    for opt in ["没有进行摸底", "摸底表农户未签署", "摸底表中没有表达延包意愿", "摸底表其它签署不齐全", 
                "特殊人员摸底不清或未统计", "户变化未统计", "矛盾纠纷未登记或处理不当", "承包地变化未摸清", "没有应确尽确"]:
        if any(opt in x for x in form_data.get("prog_2", [])):
            txt = txt.replace(f"□{opt}", f"☑{opt}")
    t2.Rows(3).Cells(4).Range.Text = txt
    t2.Rows(3).Cells(6).Range.Text = f"{scores['deduct']['p2']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p2'] > 0 else "0"

    # R4: 制定方案
    txt = t2.Rows(4).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    for opt in ["没有延包方案", "延包方案未上报", "延包方案未公示", "未召开会议讨论延包方案"]:
        short = opt.replace("延包方案", "").replace("召开会议", "")
        if any(opt in x or short in x for x in form_data.get("prog_3", [])):
            txt = txt.replace(f"□{opt}", f"☑{opt}")
    t2.Rows(4).Cells(4).Range.Text = txt
    t2.Rows(4).Cells(6).Range.Text = f"{scores['deduct']['p3']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p3'] > 0 else "0"

    # R5: 调查公示
    txt = t2.Rows(5).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    for opt in ["没有公示材料", "没有公示不足15天", "公示结果未确认", "各类资料不齐全", 
                "各类资料制作粗糙", "各类资料签署不规范", "权属证明材料不齐全", "其它证明材料不齐全"]:
        if any(opt in x for x in form_data.get("prog_4", [])):
            txt = txt.replace(f"□{opt}", f"☑{opt}")
    t2.Rows(5).Cells(4).Range.Text = txt
    t2.Rows(5).Cells(6).Range.Text = f"{scores['deduct']['p4']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p4'] > 0 else "0"

    # R6: 签订合同
    txt = t2.Rows(6).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    for opt in ["合同版本格式不正确", "合同网签率未达到95%", "没有地块示意图"]:
        short = opt.replace("合同", "")
        if any(opt in x or short in x for x in form_data.get("prog_5", [])):
            txt = txt.replace(f"□{opt}", f"☑{opt}")
    t2.Rows(6).Cells(4).Range.Text = txt
    t2.Rows(6).Cells(6).Range.Text = f"{scores['deduct']['p5']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p5'] > 0 else "0"

    # R7: 完善证书
    txt = t2.Rows(7).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    for opt in ["未进行信息共享", "未与不动产登记部门有序衔接"]:
        short = opt.replace("登记部门", "")
        if any(opt in x or short in x for x in form_data.get("prog_6", [])):
            txt = txt.replace(f"□{opt}", f"☑{opt}")
    t2.Rows(7).Cells(4).Range.Text = txt
    t2.Rows(7).Cells(6).Range.Text = f"{scores['deduct']['p6']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p6'] > 0 else "0"

    # R8: 资料归档
    txt = t2.Rows(8).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    for opt in ["档案整理第三方无涉密档案整理资质", "没有进行档案验收", "档案验收不符合相关标准"]:
        short = opt.replace("档案整理", "").replace("相关", "")
        if any(opt in x or short in x for x in form_data.get("prog_7", [])):
            txt = txt.replace(f"□{opt}", f"☑{opt}")
    t2.Rows(8).Cells(4).Range.Text = txt
    t2.Rows(8).Cells(6).Range.Text = f"{scores['deduct']['p7']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['p7'] > 0 else "0"

    # R9: 总计扣分
    t2.Rows(9).Cells(3).Range.Text = f"{scores['deduct']['prog']:.1f}".rstrip('0').rstrip('.')
    
    # R10: 重要问题描述
    issues = []
    if form_data.get("prog_1"): issues.append("成立机构：" + "、".join(form_data.get("prog_1", [])))
    if form_data.get("prog_2"): issues.append("摸底核实：" + "、".join(form_data.get("prog_2", [])))
    if form_data.get("prog_3"): issues.append("制定方案：" + "、".join(form_data.get("prog_3", [])))
    if form_data.get("prog_4"): issues.append("调查公示：" + "、".join(form_data.get("prog_4", [])))
    if form_data.get("prog_5"): issues.append("签订合同：" + "、".join(form_data.get("prog_5", [])))
    if form_data.get("prog_6"): issues.append("完善证书：" + "、".join(form_data.get("prog_6", [])))
    if form_data.get("prog_7"): issues.append("资料归档：" + "、".join(form_data.get("prog_7", [])))
    t2.Rows(10).Cells(2).Range.Text = "\n".join(issues) if issues else "无"

def fill_table_3(t3, form_data, scores):
    # R2: 大稳定、小调整
    txt = t3.Rows(2).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    for opt in ["小调整比率过大或手续不齐全", "打乱重分", "违法调整或收回承包地"]:
        if any(opt in x for x in form_data.get("policy_1", [])):
            txt = txt.replace(f"□{opt}", f"☑{opt}")
    t3.Rows(2).Cells(4).Range.Text = txt
    t3.Rows(2).Cells(6).Range.Text = f"{scores['deduct']['pol1']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol1'] > 0 else "0"

    # R3: 保障土地承包权益 (带数量)
    txt = t3.Rows(3).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    c_2_1 = int(form_data.get("policy_2_1", 0) or 0)
    c_2_2 = int(form_data.get("policy_2_2", 0) or 0)
    if c_2_1 > 0:
        txt = txt.replace("□未保障特殊群体权益", f"☑未保障特殊群体权益（{c_2_1}起）")
    if c_2_2 > 0:
        txt = txt.replace("□未保障无地户权益", f"☑未保障无地户权益（{c_2_2}起）")
    t3.Rows(3).Cells(4).Range.Text = txt
    t3.Rows(3).Cells(6).Range.Text = f"{scores['deduct']['pol2']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol2'] > 0 else "0"

    # R4: 依法收回消亡户承包地 (带数量)
    txt = t3.Rows(4).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    c_3_1 = int(form_data.get("policy_3_1", 0) or 0)
    c_3_2 = int(form_data.get("policy_3_2", 0) or 0)
    if c_3_1 > 0:
        txt = txt.replace("□没有应收尽收", f"☑没有应收尽收（{c_3_1}起）")
    if c_3_2 > 0:
        txt = txt.replace("□采用不正当方式隐匿消亡户", f"☑采用不正当方式隐匿消亡户（{c_3_2}起）")
    t3.Rows(4).Cells(4).Range.Text = txt
    t3.Rows(4).Cells(6).Range.Text = f"{scores['deduct']['pol3']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol3'] > 0 else "0"

    # R5: 严格机动地和新增耕地管理
    txt = t3.Rows(5).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    for opt in ["机动地、新增耕地处置不当", "机动地比率过高"]:
        if any(opt in x for x in form_data.get("policy_4", [])):
            txt = txt.replace(f"□{opt}", f"☑{opt}")
    t3.Rows(5).Cells(4).Range.Text = txt
    t3.Rows(5).Cells(6).Range.Text = f"{scores['deduct']['pol4']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol4'] > 0 else "0"

    # R6: 从严掌握确权确股不确地
    txt = t3.Rows(6).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    for opt in ["违背农户意愿强行推进", "确权确股不确地手续不齐全"]:
        if any(opt in x for x in form_data.get("policy_5", [])):
            txt = txt.replace(f"□{opt}", f"☑{opt}")
    t3.Rows(6).Cells(4).Range.Text = txt
    t3.Rows(6).Cells(6).Range.Text = f"{scores['deduct']['pol5']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['pol5'] > 0 else "0"

    # R7: 总计扣分
    t3.Rows(7).Cells(3).Range.Text = f"{scores['deduct']['policy']:.1f}".rstrip('0').rstrip('.')
    
    # R8: 重要问题描述
    issues = []
    if form_data.get("policy_1"): issues.append("大稳定小调整：" + "、".join(form_data.get("policy_1", [])))
    if c_2_1 > 0: issues.append(f"未保障特殊群体权益（{c_2_1}起）")
    if c_2_2 > 0: issues.append(f"未保障无地户权益（{c_2_2}起）")
    if c_3_1 > 0: issues.append(f"消亡户未应收尽收（{c_3_1}起）")
    if c_3_2 > 0: issues.append(f"不正当方式隐匿消亡户（{c_3_2}起）")
    if form_data.get("policy_4"): issues.append("机动地管理：" + "、".join(form_data.get("policy_4", [])))
    if form_data.get("policy_5"): issues.append("确权确股不确地：" + "、".join(form_data.get("policy_5", [])))
    t3.Rows(8).Cells(2).Range.Text = "\n".join(issues) if issues else "无"

def fill_table_4(t4, form_data, scores):
    # R2: 加强风险防范
    txt = t4.Rows(2).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    for opt in ["未建立矛盾纠纷处置机制", "未建立舆情处置办法", "没有矛盾纠纷处理台账"]:
        short = opt.replace("矛盾纠纷", "")
        if any(opt in x or short in x for x in form_data.get("effect_1", [])):
            txt = txt.replace(f"□{opt}", f"☑{opt}")
    t4.Rows(2).Cells(4).Range.Text = txt
    t4.Rows(2).Cells(6).Range.Text = f"{scores['deduct']['effect']:.1f}".rstrip('0').rstrip('.') if scores['deduct']['effect'] > 0 else "0"

    # R3: 总计扣分
    t4.Rows(3).Cells(3).Range.Text = f"{scores['deduct']['effect']:.1f}".rstrip('0').rstrip('.')
    
    # R4: 重要问题描述
    issues = []
    if form_data.get("effect_1"): issues.append("风险防范存在问题：" + "、".join(form_data.get("effect_1", [])))
    t4.Rows(4).Cells(2).Range.Text = "\n".join(issues) if issues else "无"

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
        
        # Replace headers in all 4 pages
        find = doc.Content.Find
        find.ClearFormatting()
        find.Replacement.ClearFormatting()
        find.Execute(
            FindText="行政区划名称：                             ",
            ReplaceWith=f"行政区划名称：{township_name:<16} ",
            Replace=2
        )
        
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
        
        # Replace header for Table 1
        find = doc.Content.Find
        find.ClearFormatting()
        find.Replacement.ClearFormatting()
        find.Execute(
            FindText="行政区划名称：                             ",
            ReplaceWith="行政区划名称：全椒县                 ",
            Replace=2
        )
        
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
        county_rec = records_by_qsdwdm.get("341124", {})
        c_scores = calculate_neiye_subscores(county_rec.get("form_data", {})) if county_rec else {"score": {"mech": 15.0}}
        t.Rows(2).Cells(1).Range.Text = "1"
        t.Rows(2).Cells(2).Range.Text = "全椒县"
        t.Rows(2).Cells(3).Range.Text = f"{c_scores['score']['mech']:.1f}".rstrip('0').rstrip('.')
        t.Rows(2).Cells(4).Range.Text = "/"
        t.Rows(2).Cells(5).Range.Text = "/"
        t.Rows(2).Cells(6).Range.Text = "/"
        t.Rows(2).Cells(7).Range.Text = f"{c_scores['score']['mech']:.1f}".rstrip('0').rstrip('.')

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
            t.Rows(13).Cells(3).Range.Text = f"{sums['mech']/count_evaluated:.1f}"
            t.Rows(13).Cells(4).Range.Text = f"{sums['prog']/count_evaluated:.1f}"
            t.Rows(13).Cells(5).Range.Text = f"{sums['policy']/count_evaluated:.1f}"
            t.Rows(13).Cells(6).Range.Text = f"{sums['effect']/count_evaluated:.1f}"
            t.Rows(13).Cells(7).Range.Text = f"{sums['total']/count_evaluated:.1f}"
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