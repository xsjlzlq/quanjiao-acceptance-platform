import requests, json

print("=== 1. 执行抽样 (自动存库并生成附件5) ===")
r = requests.post("http://127.0.0.1:8081/api/sample", json={
    "mode": 2,
    "township_code": "341124100",
    "township_name": "襄河镇"
})
print("Sampling result:", r.status_code, r.json().get("message"))
print("Generated URLs count:", len(r.json().get("urls", [])))
print("Att5 URL:", r.json().get("urls", [])[0] if r.json().get("urls") else None)

print("\n=== 2. 查询外业已抽样层级列表 ===")
r = requests.get("http://127.0.0.1:8081/api/waiye/hierarchy")
hier = r.json()
print("Hierarchy code:", hier.get("code"), "Total groups:", hier.get("total_groups"))
if hier.get("tree"):
    first_ts = hier["tree"][0]
    print("First township:", first_ts["text"], "villages:", len(first_ts["children"]))
    first_vill = first_ts["children"][0]
    first_group = first_vill["children"][0]
    g_code = first_group["group_code"]
    print("Selected group:", first_group["text"], "code:", g_code)

    print("\n=== 3. 查询该组地块清单 ===")
    r_samples = requests.get(f"http://127.0.0.1:8081/api/waiye/group_samples?group_code={g_code}")
    samples = r_samples.json().get("data", [])
    print(f"Loaded {len(samples)} parcels for group {g_code}")
    for s in samples[:3]:
        print(f"  ID:{s['id']} | {s['cbfmc']} ({s['cbfbm_short']}) | {s['dkmc']} ({s['dkbm_short']}) | 面积:{s['scmj']}亩")

    print("\n=== 4. 对错误项打X并保存 ===")
    if samples:
        # Mark first parcel with 2 error X's
        samples[0]["area_acknowledged"] = "X"
        samples[0]["rights_correct"] = "X"
        if len(samples) > 1:
            samples[1]["bound_correct"] = "X"
            samples[1]["satisfaction"] = "不满意"

        r_save = requests.post("http://127.0.0.1:8081/api/waiye/save_records", json={
            "records": samples
        })
        print("Save records result:", r_save.json())

    print("\n=== 5. 导出附件8 (外业核查记录表) ===")
    r_att8 = requests.post("http://127.0.0.1:8081/api/export_waiye_att8", json={
        "township_name": first_ts["township_name"],
        "village_name": first_vill["village_name"],
        "group_name": first_group["group_name"],
        "group_code": g_code
    })
    print("Export 附件8 URL:", r_att8.json().get("url"))

print("\n=== 6. 导出附件9 (全县外业得分表) ===")
r_att9 = requests.get("http://127.0.0.1:8081/api/export_waiye_att9")
print("Export 附件9 URL:", r_att9.json().get("url"))