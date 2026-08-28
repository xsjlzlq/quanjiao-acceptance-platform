import os, time, shutil, re, win32com.client, pythoncom
from doc_exporter import export_neiye_att7

t0 = time.time()
records = {
    "341124": {"form_data": {"mech_1": ["未制定方案"]}},
    "341124100": {"form_data": {"mech_1": ["直接套用上级方案"], "policy_2_1": 1}}
}
url = export_neiye_att7(records)
print("Att7 exported to:", url, f"in {time.time()-t0:.2f}s")