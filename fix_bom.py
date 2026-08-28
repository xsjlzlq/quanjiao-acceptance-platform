with open('backend/main.py', 'r', encoding='utf-8-sig') as f:
    code = f.read()
with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("BOM removed")
