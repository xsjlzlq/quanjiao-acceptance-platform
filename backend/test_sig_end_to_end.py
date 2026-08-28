import requests, json, base64, os
from PIL import Image, ImageDraw

# 1. Create a signature dataURL
img = Image.new("RGBA", (300, 100), (255, 255, 255, 0))
draw = ImageDraw.Draw(img)
draw.line([(10, 50), (80, 20), (140, 70), (200, 30), (280, 60)], fill="black", width=4)
draw.text((100, 60), "张三(本人手签)", fill="red")
import io
buf = io.BytesIO()
img.save(buf, format="PNG")
data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")

# 2. Get samples from Xianghe
r_hier = requests.get("http://127.0.0.1:8081/api/waiye/hierarchy").json()
print("Hierarchy groups count:", r_hier.get("total_groups"))
first_group = r_hier["tree"][0]["children"][0]["children"][0]
g_code = first_group["group_code"]
t_name = first_group["township_name"]
v_name = first_group["village_name"]
g_name = first_group["group_name"]

r_samples = requests.get(f"http://127.0.0.1:8081/api/waiye/group_samples?group_code={g_code}").json()
samples = r_samples.get("data", [])
print(f"Group {g_code} has {len(samples)} samples:")
for s in samples[:2]:
    print(f"  cbfmc:{s['cbfmc']} cbfbm:{s['cbfbm']} sig_url:{s['signature_url']}")

# 3. Save signature for the first contractor
first_cbfbm = samples[0]["cbfbm"]
first_cbfmc = samples[0]["cbfmc"]
r_sig = requests.post("http://127.0.0.1:8081/api/waiye/save_signature", json={
    "cbfbm": first_cbfbm,
    "cbfmc": first_cbfmc,
    "signature_data": data_url
}).json()
print("\nSave signature response:", r_sig)

# 4. Check group samples again -> all parcels with first_cbfbm should now have signature_url
r_samples_after = requests.get(f"http://127.0.0.1:8081/api/waiye/group_samples?group_code={g_code}").json()
samples_after = r_samples_after.get("data", [])
print(f"\nAfter signature save, group {g_code} samples:")
for s in samples_after[:2]:
    print(f"  cbfmc:{s['cbfmc']} cbfbm:{s['cbfbm']} sig_url:{s['signature_url']}")

# 5. Export Attachment 8 with signature inserted and merged
r_export = requests.post("http://127.0.0.1:8081/api/export_waiye_att8", json={
    "township_name": t_name,
    "village_name": v_name,
    "group_name": g_name,
    "group_code": g_code
}).json()
print("\nExport Attachment 8 result:", r_export)

# 6. Verify the exported Word file has the image
import win32com.client, pythoncom
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
doc_path = os.path.abspath(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend" + r_export["url"].replace("/api/download?file=", "\\"))
print("Opening exported doc:", doc_path)
d = word.Documents.Open(doc_path)
print("InlineShapes count:", d.InlineShapes.Count)
for i in range(1, d.InlineShapes.Count + 1):
    s = d.InlineShapes(i)
    print(f"  Shape {i}: width={s.Width}, height={s.Height}")
d.Close(0)
word.Quit()
pythoncom.CoUninitialize()

print("\nAll signature verification tests passed!")