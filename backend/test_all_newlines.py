import win32com.client, os, pythoncom, shutil

def test_all_tables_newlines():
    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    
    base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
    tpl = os.path.join(base_dir, "附件", "附件6.doc")
    out_path = os.path.join(base_dir, "backend", "downloads", "test_all_newlines.doc")
    shutil.copy(tpl, out_path)
    
    doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
    
    def update_cell_checkboxes(cell, replacements):
        txt = cell.Range.Text.replace("\x07", "")
        for old_val, new_val in replacements:
            txt = txt.replace(old_val, new_val)
        while txt.endswith("\r"):
            txt = txt[:-1]
        cell.Range.Text = txt

    # Table 2 R3: 摸底核实
    t2 = doc.Tables(2)
    c4 = t2.Rows(3).Cells(4)
    update_cell_checkboxes(c4, [
        ("□没有进行摸底", "☑没有进行摸底"),
        ("□承包地变化未摸清", "☑承包地变化未摸清")
    ])
    
    # Table 3 R3: 保障土地承包权益
    t3 = doc.Tables(3)
    c4_t3 = t3.Rows(3).Cells(4)
    update_cell_checkboxes(c4_t3, [
        ("□未保障特殊群体权益", "☑未保障特殊群体权益（2起）")
    ])
    
    with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\all_newlines_res.txt", "w", encoding="utf-8") as out:
        out.write("=== T2 R3 (摸底核实) ===\n")
        for line in t2.Rows(3).Cells(4).Range.Text.replace("\x07", "").split("\r"):
            if line:
                out.write(f"  Line: {line}\n")
                
        out.write("\n=== T3 R3 (保障权益) ===\n")
        for line in t3.Rows(3).Cells(4).Range.Text.replace("\x07", "").split("\r"):
            if line:
                out.write(f"  Line: {line}\n")
                
    doc.SaveAs2(FileName=out_path, FileFormat=0)
    doc.Close(0)
    word.Quit()
    pythoncom.CoUninitialize()
    print("All tables newline test finished!")

test_all_tables_newlines()