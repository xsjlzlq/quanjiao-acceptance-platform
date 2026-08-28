import sys

with open('backend/main.py', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace("WHERE qsdwdm = :vc", "WHERE qsdwdm::text = :vc")

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched main.py")
