import sys

with open('frontend/vite.config.js', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace("allowedHosts: 'all',", "host: '0.0.0.0',\n    allowedHosts: true,")

with open('frontend/vite.config.js', 'w', encoding='utf-8') as f:
    f.write(code)

print("Vite config fixed")
