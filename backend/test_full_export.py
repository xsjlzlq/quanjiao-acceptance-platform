import win32com.client, os, pythoncom, shutil

def test_full_export_township():
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件6.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "test_att6_township.doc")
    shutil.copy(tpl, out_path)
    
    doc = word.Documents.Open(out_path)
    township_name = "襄河镇"
    
    # Update headers
    for p in doc.Paragraphs:
        t = p.Range.Text
        if "行政区划名称：" in t and "验收内容：" in t:
            for c_name in ["机制运行", "程序规范", "政策落实", "工作成效"]:
                if c_name in t:
                    p.Range.Text = f"行政区划名称：{township_name}" + " "*20 + f"验收内容：{c_name}" + " "*20 + "2026 年    月    日\r"
                    break

    # Mock form data
    form_data = {
        "mech_1": ["未制定方案"],
        "mech_2": ["支付不及时"],
        "mech_3": ["没有宣传材料"],
        "mech_4": ["没有培训材料"],
        "prog_1": ["未召开会议"],
        "prog_2": ["没有进行摸底", "户变化未统计"],
        "prog_3": ["没有延包方案"],
        "prog_4": ["公示结果未确认", "各类资料不齐全"],
        "prog_5": ["没有地块示意图"],
        "prog_6": ["未进行信息共享"],
        "prog_7": ["没有进行档案验收"],
        "policy_1": ["打乱重分"],
        "policy_2_1": 2, # 2起
        "policy_2_2": 0,
        "policy_3_1": 1, # 1起
        "policy_3_2": 0,
        "policy_4": ["机动地比率过高"],
        "policy_5": ["违背农户意愿强行推进"],
        "effect_1": ["未建立矛盾纠纷处置机制"]
    }

    # === Table 1: 机制运行 ===
    t1 = doc.Tables(1)
    
    # R2: 配套延包
    d_m1 = 2.0 if form_data.get("mech_1") else 0.0
    txt = t1.Rows(2).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    for opt in ["未制定方案", "直接套用上级方案", "分工不明确", "制定程序不合法"]:
        if any(opt in x for x in form_data.get("mech_1", [])):
            txt = txt.replace(f"□{opt}", f"☑{opt}")
    t1.Rows(2).Cells(4).Range.Text = txt
    t1.Rows(2).Cells(6).Range.Text = str(d_m1) if d_m1 > 0 else "0"
    
    # R3: 经费保障
    d_m2 = 0.0
    txt = t1.Rows(3).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    if any("支付不规范" in x for x in form_data.get("mech_2", [])):
        txt = txt.replace("□支付不规范", "☑支付不规范"); d_m2 += 4.0
    if any("支付不及时" in x for x in form_data.get("mech_2", [])):
        txt = txt.replace("□支付不及时", "☑支付不及时"); d_m2 += 4.0
    if any("兜底" in x for x in form_data.get("mech_2", [])):
        txt = txt.replace("□经费没有县级兜底", "☑经费没有县级兜底"); d_m2 += 2.0
    d_m2 = min(d_m2, 10.0)
    t1.Rows(3).Cells(4).Range.Text = txt
    t1.Rows(3).Cells(6).Range.Text = str(d_m2) if d_m2 > 0 else "0"

    # R4: 宣传
    d_m3 = 2.0 if form_data.get("mech_3") else 0.0
    txt = t1.Rows(4).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    if form_data.get("mech_3"):
        txt = txt.replace("□没有宣传材料", "☑没有宣传材料")
    t1.Rows(4).Cells(4).Range.Text = txt
    t1.Rows(4).Cells(6).Range.Text = str(d_m3) if d_m3 > 0 else "0"

    # R5: 培训
    d_m4 = 0.0
    txt = t1.Rows(5).Cells(4).Range.Text.replace("\x07", "").replace("\r", "")
    for opt in ["没有培训材料", "没有分批次培训", "培训材料不齐全", "培训未覆盖县乡村组"]:
        short_opt = opt.replace("县", "")
        if any(opt in x or short_opt in x for x in form_data.get("mech_4", [])):
            txt = txt.replace(f"□{opt}", f"☑{opt}")
            d_m4 += 0.5
    d_m4 = min(d_m4, 1.0)
    t1.Rows(5).Cells(4).Range.Text = txt
    t1.Rows(5).Cells(6).Range.Text = str(d_m4) if d_m4 > 0 else "0"

    tot_m = d_m1 + d_m2 + d_m3 + d_m4
    t1.Rows(6).Cells(3).Range.Text = str(tot_m)
    t1.Rows(7).Cells(2).Range.Text = "机制运行存在问题已在表内标明。"

    doc.Save()
    doc.Close(False)
    word.Quit()
    pythoncom.CoUninitialize()
    print("Full export test passed!")

test_full_export_township()