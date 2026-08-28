import os, time, shutil, re, win32com.client, pythoncom
from doc_exporter import calculate_neiye_subscores, fill_table_1, fill_table_2, fill_table_3, fill_table_4

def test_diag_town():
    t0 = time.time()
    print("1. CoInitialize")
    pythoncom.CoInitialize()
    
    print("2. DispatchEx Word")
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件6.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "diag_town.doc")
    shutil.copy(tpl, out_path)
    
    print("3. Documents.Open")
    doc = word.Documents.Open(out_path)
    
    print("4. Find Replace Header")
    find = doc.Content.Find
    find.ClearFormatting()
    find.Replacement.ClearFormatting()
    find.Execute(
        FindText="行政区划名称：                             ",
        ReplaceWith="行政区划名称：襄河镇                    ",
        Replace=2
    )
    
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
        "policy_2_1": 2,
        "policy_2_2": 0,
        "policy_3_1": 1,
        "policy_3_2": 0,
        "policy_4": ["机动地比率过高"],
        "policy_5": ["违背农户意愿强行推进"],
        "effect_1": ["未建立矛盾纠纷处置机制"]
    }
    
    scores = calculate_neiye_subscores(form_data)
    
    print("5. Fill Table 1")
    fill_table_1(doc.Tables(1), form_data, scores)
    print(f"   Table 1 done in {time.time()-t0:.2f}s")
    
    print("6. Fill Table 2")
    fill_table_2(doc.Tables(2), form_data, scores)
    print(f"   Table 2 done in {time.time()-t0:.2f}s")
    
    print("7. Fill Table 3")
    fill_table_3(doc.Tables(3), form_data, scores)
    print(f"   Table 3 done in {time.time()-t0:.2f}s")
    
    print("8. Fill Table 4")
    fill_table_4(doc.Tables(4), form_data, scores)
    print(f"   Table 4 done in {time.time()-t0:.2f}s")
    
    print("9. Save")
    doc.Save()
    print("10. Close")
    doc.Close(0)
    print("11. Quit")
    word.Quit()
    pythoncom.CoUninitialize()
    print(f"ALL DONE in {time.time()-t0:.2f}s!")

test_diag_town()