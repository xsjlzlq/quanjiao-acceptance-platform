import win32com.client, os, pythoncom, shutil

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件6.doc")
out_path = os.path.join(base_dir, "backend", "downloads", "test_spacing2.doc")
shutil.copy(tpl, out_path)

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)

for full_area_name in ["全椒县襄河镇", "全椒县"]:
    spaces_1 = " " * max(2, 29 - len(full_area_name) * 2)
    spaces_2 = " " * 28
    hdr_text = f"行政区划名称：{full_area_name}{spaces_1}验收内容：机制运行{spaces_2}2026 年       月      日"
    print(f"[{full_area_name}] len={len(hdr_text)}")

doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()