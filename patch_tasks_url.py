with open('frontend/src/views/Tasks.vue', 'r', encoding='utf-8') as f:
    code = f.read()

code = code.replace("window.open('http://localhost:8000' + url, '_blank');", "window.open(url, '_blank');")

with open('frontend/src/views/Tasks.vue', 'w', encoding='utf-8') as f:
    f.write(code)
print("Tasks.vue URL patched")
