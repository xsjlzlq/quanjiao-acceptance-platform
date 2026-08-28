import sys

with open('frontend/vite.config.js', 'r', encoding='utf-8') as f:
    code = f.read()

# Add allowedHosts configuration
if "allowedHosts: true" not in code and "allowedHosts: 'all'" not in code:
    code = code.replace("port: 8000,", "port: 8000,\n    allowedHosts: 'all',")
    with open('frontend/vite.config.js', 'w', encoding='utf-8') as f:
        f.write(code)
    print("Patched vite.config.js")
else:
    print("Already patched")
