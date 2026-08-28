import sys

# 1. Update vite.config.js
with open('frontend/vite.config.js', 'r', encoding='utf-8') as f:
    v_code = f.read()

v_code = v_code.replace("port: 8000,", "port: 3000,")

with open('frontend/vite.config.js', 'w', encoding='utf-8') as f:
    f.write(v_code)

# 2. Update start_dev.ps1
with open('start_dev.ps1', 'r', encoding='utf-8') as f:
    s_code = f.read()

s_code = s_code.replace('-LocalPort 8000', '-LocalPort 3000')

with open('start_dev.ps1', 'w', encoding='utf-8') as f:
    f.write(s_code)

print("Ports patched back to 3000.")
