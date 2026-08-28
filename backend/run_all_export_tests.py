from test_new_exporter import export_neiye_att6_township, export_neiye_att6_county, export_neiye_att7

sample_form = {
    "mech_1": ["未制定方案"],
    "mech_2": ["支付不及时"],
    "mech_3": ["没有宣传材料"],
    "mech_4": ["没有培训材料"],
    "prog_1": ["未召开会议"],
    "prog_2": ["没有进行摸底", "户变化未统计"],
    "prog_3": ["没有延包方案"],
    "prog_4": ["公示结果未确认", "各类资料不齐全"],
    "prog_5": ["没有地块示意图"],
    "prog_6": ["未进行信息共享"],
    "prog_7": ["没有进行档案验收"],
    "policy_1": ["打乱重分"],
    "policy_2_1": 2,
    "policy_2_2": 0,
    "policy_3_1": 1,
    "policy_3_2": 0,
    "policy_4": ["机动地比率过高"],
    "policy_5": ["违背农户意愿强行推进"],
    "effect_1": ["未建立矛盾纠纷处置机制"]
}

url1 = export_neiye_att6_township("襄河镇", sample_form)
print("1. Township att6 URL:", url1)

url2 = export_neiye_att6_county(sample_form)
print("2. County att6_1/4 URL:", url2)

url3 = export_neiye_att7({
    "341124": {"form_data": sample_form, "score": 6.5},
    "341124100": {"form_data": sample_form, "score": 38.5}
})
print("3. County att7 URL:", url3)