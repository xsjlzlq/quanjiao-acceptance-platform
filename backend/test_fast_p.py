import win32com.client, os, pythoncom, shutil, time

t0 = time.time()
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件6.doc")
out_path = os.path.join(base_dir, "backend", "downloads", "test_fast_p.doc")
shutil.copy(tpl, out_path)

doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)

# Direct access to known paragraphs:
p_indices = [
    (3, "机制运行"),
    (68, "程序规范"),
    (188, "政策落实"),
    (253, "工作成效")
]

township_name = "襄河镇"
full_name = "全椒县" + township_name if not township_name.startswith("全椒县") else township_name

for idx, c_name in p_indices:
    p = doc.Paragraphs(idx)
    # verify
    if "行政区划名称" in p.Range.Text:
        p.Range.Text = f"行政区划名称：{full_name:<16}  验收内容：{c_name:<16}  2026 年       月      日\r"
        print(f"P{idx} replaced successfully!")

doc.SaveAs2(FileName=out_path, FileFormat=0)
doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()
print(f"Direct paragraph access finished in {time.time()-t0:.2f}s!")