import time
from doc_exporter import export_neiye_att6_county, export_neiye_att6_township, export_neiye_att7

sample_form = {
    "mech_1": ["未制定方案"],
    "policy_2_1": 1
}

t0 = time.time()
u1 = export_neiye_att6_county(sample_form)
print(f"1. County Att6 (1/4): {u1} in {time.time()-t0:.2f}s")

t1 = time.time()
u2 = export_neiye_att6_township("襄河镇", sample_form)
print(f"2. Township Att6: {u2} in {time.time()-t1:.2f}s")

t2 = time.time()
u3 = export_neiye_att7({"341124": {"form_data": sample_form}, "341124100": {"form_data": sample_form}})
print(f"3. Att7: {u3} in {time.time()-t2:.2f}s")