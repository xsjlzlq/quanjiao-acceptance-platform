import time
from doc_exporter import export_neiye_att6_township, export_neiye_att6_county, export_neiye_att7

sample_form = {
    "mech_1": ["未制定方案"],
    "policy_2_1": 1
}

t0 = time.time()
u1 = export_neiye_att6_county(sample_form)
print("County:", u1, f"({time.time()-t0:.2f}s)")

t1 = time.time()
u2 = export_neiye_att6_township("襄河镇", sample_form)
print("Township:", u2, f"({time.time()-t1:.2f}s)")

t2 = time.time()
u3 = export_neiye_att7({"341124": {"form_data": sample_form}, "341124100": {"form_data": sample_form}})
print("Att7:", u3, f"({time.time()-t2:.2f}s)")