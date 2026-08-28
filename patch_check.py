import re
with open('frontend/src/views/NeiyeForm.vue', 'r', encoding='utf-8') as f:
    code = f.read()

matches = re.findall(r'<van-checkbox name="(.*?)"', code)
print(matches[:15])