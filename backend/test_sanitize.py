import re

def sanitize_filename(name):
    clean = re.sub(r'[\\/*?:"<>|]', "", str(name)).strip()
    return clean if clean else "乡镇"

print("Sanitize test 1:", sanitize_filename("襄河镇"))
print("Sanitize test 2:", sanitize_filename("襄/河?镇*"))