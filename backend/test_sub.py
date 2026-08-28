import subprocess, json, time, os

t0 = time.time()
base = r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend"
param_path = os.path.join(base, "temp_param.json")
with open(param_path, "w", encoding="utf-8") as f:
    json.dump({"form_data": {"mech_1": ["未制定方案"]}}, f)

proc = subprocess.run(
    ["python", "export_worker.py", "att6_county", param_path],
    capture_output=True,
    text=True,
    encoding="utf-8",
    cwd=base
)
print("Worker stdout:", proc.stdout.strip())
print(f"Total time: {time.time()-t0:.2f}s")