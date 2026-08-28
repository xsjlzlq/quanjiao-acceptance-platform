import sys

with open('backend/main.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace qsdwdm LIKE to qsdwdm::text LIKE
code = code.replace("qsdwdm LIKE :ts AND qsdwdm NOT LIKE '%00'", "qsdwdm::text LIKE :ts AND qsdwdm::text NOT LIKE '%00'")
code = code.replace("cbfbm LIKE :code", "cbfbm::text LIKE :code")

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("Patched LIKE queries to cast to text")
