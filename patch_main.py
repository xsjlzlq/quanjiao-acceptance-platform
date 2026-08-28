import sys

with open('backend/main.py', 'r', encoding='utf-8') as f:
    code = f.read()

# We need to import the new functions
code = "from doc_exporter import export_docs, export_att4\n" + code

# Replace the block generating excel files
old_block_1 = """        df_stats = pd.DataFrame(stats)
        att5_path = f"downloads/附件5_抽样统计表_{req.township_code}.xlsx"
        df_stats.to_excel(att5_path, index=False)
        
        df_att8 = pd.DataFrame(out_att8_data)
        att8_path = f"downloads/附件8_外业核查记录表_{req.township_code}.xlsx"
        df_att8.to_excel(att8_path, index=False)
        
        return {
            "code": 200, 
            "message": "抽样成功",
            "stats": stats,
            "att5_url": f"/api/download?file={att5_path}",
            "att8_url": f"/api/download?file={att8_path}"
        }"""

new_block_1 = """        import asyncio
        att5_url, att8_url = await asyncio.to_thread(export_docs, stats, out_att8_data, req.township_code)
        
        return {
            "code": 200, 
            "message": "抽样成功",
            "stats": stats,
            "att5_url": att5_url,
            "att8_url": att8_url
        }"""

code = code.replace(old_block_1, new_block_1)

old_block_2 = """@app.get("/api/generate_att4")
async def generate_att4():
    os.makedirs("downloads", exist_ok=True)
    path = "downloads/附件4_成果检查验收申请表.xlsx"
    df = pd.DataFrame([
        {"申请单位": "", "主要负责人及职务": "", "联系电话": "", "联系人及职务": "", "联系电话2": ""},
        {"承包起止时间": "", "网签平台": "", "农户总数(户)": "", "延包合同签订数(份)": "", "确权总面积(亩)": ""},
        {"延包合同面积(亩)": "", "暂缓延包农户数(户)": "", "暂缓延包面积(亩)": "", "县级意见": ""}
    ])
    df.to_excel(path, index=False)
    return {"code": 200, "url": f"/api/download?file={path}"}"""

new_block_2 = """@app.get("/api/generate_att4")
async def generate_att4():
    import asyncio
    url = await asyncio.to_thread(export_att4)
    return {"code": 200, "url": url}"""

code = code.replace(old_block_2, new_block_2)

with open('backend/main.py', 'w', encoding='utf-8') as f:
    f.write(code)
print("main.py patched")
