import sys
import re

with open('backend/main.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add manual_sample_count
code = code.replace("group_name: Optional[str] = None", "group_name: Optional[str] = None\n    manual_sample_count: Optional[int] = None")

# Replace logic
bad_logic = "sample_size = max(1, int(total_cbf * 0.05)) if total_cbf > 0 else 0"
good_logic = """import math
            if req.mode == 1 and req.manual_sample_count is not None and req.manual_sample_count > 0:
                sample_size = min(total_cbf, req.manual_sample_count)
            else:
                sample_size = math.ceil(total_cbf * 0.05) if total_cbf > 0 else 0"""

code = code.replace(bad_logic, good_logic)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(code)

print("Logic patched.")
