import pandas as pd

df = pd.DataFrame([
    {
        "发包方编码": "34112410000801",
        "乡镇名": "襄河镇",
        "村名": "南屏社区",
        "组名": "封巷组",
        "抽样农户数": 2
    },
    {
        "发包方编码": "34112410000802",
        "乡镇名": "襄河镇",
        "村名": "南屏社区",
        "组名": "张黄组",
        "抽样农户数": ""
    }
])
df.to_excel("frontend/test_upload.xlsx", index=False)
print("Test Excel created.")
