def format_score(val):
    if val is None or val == "": return ""
    f = float(val)
    if f.is_integer():
        return str(int(f))
    return f"{f:.1f}"

def format_avg(val):
    if val is None: return ""
    return f"{float(val):.1f}"

# Test calculation
county_mech = 12.5
xianghe_mech = 9.0
dashu_mech = 14.5

count_mech = 3
sum_mech = county_mech + xianghe_mech + dashu_mech
avg_mech = sum_mech / count_mech

print(f"Sum: {sum_mech}, Count: {count_mech}, Avg: {avg_mech}, Formatted: {format_avg(avg_mech)}")