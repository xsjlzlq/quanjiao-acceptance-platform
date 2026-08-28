with open("backend/doc_exporter.py", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace('.Range.Text = "\n".join(issues)', '.Range.Text = "\\n".join(issues)')

with open("backend/doc_exporter.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Fixed syntax error")