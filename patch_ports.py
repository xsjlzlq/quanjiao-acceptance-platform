import sys

# 1. Update vite.config.js
with open('frontend/vite.config.js', 'r', encoding='utf-8') as f:
    v_code = f.read()

v_code = v_code.replace("port: 3000", "port: 8000")
v_code = v_code.replace("http://localhost:8000", "http://localhost:8080")

with open('frontend/vite.config.js', 'w', encoding='utf-8') as f:
    f.write(v_code)

# 2. Update start_dev.ps1
with open('start_dev.ps1', 'r', encoding='utf-8') as f:
    s_code = f.read()

s_code = s_code.replace('"--port", "8000"', '"--port", "8080"')
s_code = s_code.replace('-LocalPort 3000', '-LocalPort 8000')
s_code = s_code.replace('-LocalPort 8000 -ErrorAction', '-LocalPort 8080 -ErrorAction') # Careful, might replace twice if not precise

with open('start_dev.ps1', 'w', encoding='utf-8') as f:
    # Manual careful replacement
    lines = s_code.split('\n')
    for i, line in enumerate(lines):
        if '"--port"' in line:
            lines[i] = line.replace('8000', '8080')
        if 'LocalPort 3000' in line:
            lines[i] = line.replace('3000', '8000')
        elif 'LocalPort 8000' in line and '"--port"' not in line:
            lines[i] = line.replace('8000', '8080')
    f.write('\n'.join(lines))

print("Ports patched.")
