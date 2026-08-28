import win32com.client, os, pythoncom, shutil

base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
tpl = os.path.join(base_dir, "附件", "附件6.doc")
out_path = os.path.join(base_dir, "backend", "downloads", "test_rng_end.doc")
shutil.copy(tpl, out_path)

pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False

doc = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)

contents = ["机制运行", "程序规范", "政策落实", "工作成效"]
full_area_name = "全椒县襄河镇"

for idx in range(1, doc.Tables.Count + 1):
    t = doc.Tables(idx)
    pre_range = doc.Range(0, t.Range.Start)
    header_p = pre_range.Paragraphs(pre_range.Paragraphs.Count)
    c_name = contents[idx - 1]
    
    rng = header_p.Range
    rng.End = rng.End - 1
    rng.Text = f"行政区划名称：{full_area_name:<16}  验收内容：{c_name:<16}  2026 年       月      日"

# Verify all 4 headers
with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\rng_end_res.txt", "w", encoding="utf-8") as out:
    for idx in range(1, doc.Tables.Count + 1):
        t = doc.Tables(idx)
        pre_range = doc.Range(0, t.Range.Start)
        header_p = pre_range.Paragraphs(pre_range.Paragraphs.Count)
        txt = header_p.Range.Text.strip().replace(chr(13),'').replace(chr(7),'')
        out.write(f"Table {idx} Header: {txt}\n")

doc.SaveAs2(FileName=out_path, FileFormat=0)
doc.Close(0)
word.Quit()
pythoncom.CoUninitialize()
print("rng_end test finished!")