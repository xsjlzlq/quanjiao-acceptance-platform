import sys
import json
import os
from doc_exporter import export_neiye_att6_township, export_neiye_att6_county, export_neiye_att7

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"code": 400, "message": "Missing arguments"}))
        return

    action = sys.argv[1]
    param_file = sys.argv[2]
    
    with open(param_file, "r", encoding="utf-8") as f:
        input_data = json.load(f)
    
    try:
        if action == "att6_township":
            name = input_data.get("township_name", "默认乡镇")
            form_data = input_data.get("form_data", {})
            url = export_neiye_att6_township(name, form_data)
            print(json.dumps({"code": 200, "url": url}))
        elif action == "att6_county":
            form_data = input_data.get("form_data", {})
            url = export_neiye_att6_county(form_data)
            print(json.dumps({"code": 200, "url": url}))
        elif action == "att7":
            records = input_data.get("records", {})
            url = export_neiye_att7(records)
            print(json.dumps({"code": 200, "url": url}))
        else:
            print(json.dumps({"code": 400, "message": f"Unknown action: {action}"}))
    except Exception as e:
        print(json.dumps({"code": 500, "message": str(e)}))

if __name__ == "__main__":
    main()