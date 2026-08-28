import win32com.client, os, pythoncom, shutil

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件6.doc")
out_path = os.path.join(base_dir, "backend", "downloads", "test_p_replace.doc")
shutil.copy(tpl, out_path)

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
doc = word.Documents.Open(out_path)

headers = [
    (3, "机制运行"),
    (68, "程序规范"),
    (188, "政策落实"),
    (253, "工作成效")
]

for p_idx, c_name in headers:
    p = doc.Paragraphs(p_idx)
    # preserve paragraph formatting
    p.Range.Text = f"行政区划名称：襄河镇" + " "*20 + f"验收内容：{c_name}" + " "*20 + "2026 年    月    日\r"

doc.Save()
doc.Close(False)
word.Quit()
pythoncom.CoUninitialize()
print("Paragraphs updated successfully!")