import re

with open("backend/doc_exporter.py", "r", encoding="utf-8") as f:
    text = f.read()

# For fill_table_1
t1_issues = """    # R7: 重要问题描述
    issues = []
    if form_data.get("mech_1"): issues.extend(form_data.get("mech_1", []))
    if form_data.get("mech_2"): issues.extend(form_data.get("mech_2", []))
    if form_data.get("mech_3"): issues.extend(form_data.get("mech_3", []))
    if form_data.get("mech_4"): issues.extend(form_data.get("mech_4", []))
    t1.Rows(7).Cells(2).Range.Text = "\\n".join(issues) if issues else "无" """

text = re.sub(r'    # R7: 重要问题描述\n    issues = \[\]\n(?:    if .*?form_data\.get.*?\n)+    t1\.Rows\(7\)\.Cells\(2\)\.Range\.Text = .*', t1_issues, text)


# For fill_table_2
t2_issues = """    # R10: 重要问题描述
    issues = []
    if form_data.get("prog_1"): issues.extend(form_data.get("prog_1", []))
    if form_data.get("prog_2"): issues.extend(form_data.get("prog_2", []))
    if form_data.get("prog_3"): issues.extend(form_data.get("prog_3", []))
    if form_data.get("prog_4"): issues.extend(form_data.get("prog_4", []))
    if form_data.get("prog_5"): issues.extend(form_data.get("prog_5", []))
    if form_data.get("prog_6"): issues.extend(form_data.get("prog_6", []))
    if form_data.get("prog_7"): issues.extend(form_data.get("prog_7", []))
    t2.Rows(10).Cells(2).Range.Text = "\\n".join(issues) if issues else "无" """

text = re.sub(r'    # R10: 重要问题描述\n    issues = \[\]\n(?:    if .*?form_data\.get.*?\n)+    t2\.Rows\(10\)\.Cells\(2\)\.Range\.Text = .*', t2_issues, text)


# For fill_table_3
t3_issues = """    # R8: 重要问题描述
    issues = []
    if form_data.get("policy_1"): issues.extend(form_data.get("policy_1", []))
    if c_2_1 > 0: issues.append(f"未保障特殊群体权益（{c_2_1}起）")
    if c_2_2 > 0: issues.append(f"未保障无地户权益（{c_2_2}起）")
    if c_3_1 > 0: issues.append(f"消亡户未应收尽收（{c_3_1}起）")
    if c_3_2 > 0: issues.append(f"不正当方式隐匿消亡户（{c_3_2}起）")
    if form_data.get("policy_4"): issues.extend(form_data.get("policy_4", []))
    if form_data.get("policy_5"): issues.extend(form_data.get("policy_5", []))
    t3.Rows(8).Cells(2).Range.Text = "\\n".join(issues) if issues else "无" """

text = re.sub(r'    # R8: 重要问题描述\n    issues = \[\]\n(?:    if .*?issues\.append.*?\n)+    t3\.Rows\(8\)\.Cells\(2\)\.Range\.Text = .*', t3_issues, text)


# For fill_table_4
t4_issues = """    # R4: 重要问题描述
    issues = []
    if form_data.get("effect_1"): issues.extend(form_data.get("effect_1", []))
    t4.Rows(4).Cells(2).Range.Text = "\\n".join(issues) if issues else "无" """

text = re.sub(r'    # R4: 重要问题描述\n    issues = \[\]\n(?:    if .*?form_data\.get.*?\n)+    t4\.Rows\(4\)\.Cells\(2\)\.Range\.Text = .*', t4_issues, text)

with open("backend/doc_exporter.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Patched fill_tables in doc_exporter.py")