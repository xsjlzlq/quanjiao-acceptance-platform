import sys

with open('backend/doc_exporter.py', 'r', encoding='utf-8') as f:
    code = f.read()

bad_line = 'rng.Text = f"   乡镇：{township_name} \\t行政村：{v_name} \\t村民小组：{g_name} \\t 2026 年    月    日"'
good_line = 'rng.Text = f"   乡镇：{township_name} \\t行政村：{v_name} \\t村民小组：{g_name}" + " "*35 + "2026 年    月    日"'

code = code.replace(bad_line, good_line)

with open('backend/doc_exporter.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Spacing fixed")
