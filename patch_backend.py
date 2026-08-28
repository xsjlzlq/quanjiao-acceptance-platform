import sys

with open('backend/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("code = r[0]", "code = str(r[0])")

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Patched backend/main.py")
