$apiCode = @"

class WaiyeRecord(BaseModel):
    cbfbm: str
    dkbm: str
    result: dict
    timestamp: int

class SyncRequest(BaseModel):
    records: list[WaiyeRecord]

@app.post("/api/sync-waiye")
async def sync_waiye(req: SyncRequest):
    # 这里真实业务中应写入 postgres 的外业核查结果表中
    # 为了连通链路，这里仅作打印和成功返回，并将得分入库
    # 外业程序规范总分20分，满意度10分（农户维度/地块维度计算）
    print(f"收到 {len(req.records)} 条外业核查数据")
    for r in req.records:
        area_match = int(r.result.get('area_match', 1))
        bound_match = int(r.result.get('bound_match', 1))
        satisfaction = int(r.result.get('satisfaction', 1))
        
        # 计分逻辑: (假定一块地不对，按文档中“每发现一项扣0.5分”的逻辑)
        # 外业得分 = 20 - (错误数 * 0.5)
        # 满意度得分 = (满意数 / 抽查数) * 10
        # 这里仅在终端打印，后期可以持久化并生成《全椒县县级自查得分汇总表》
        print(f"地块 {r.dkbm} 提交: 面积认可={area_match}, 四至正确={bound_match}, 满意={satisfaction}")
        
    return {"code": 200, "message": "外业核查数据同步成功"}
"@
Add-Content -Path backend/main.py -Value $apiCode -Encoding UTF8
