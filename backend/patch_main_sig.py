with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Add base64 and Response import
if "import base64" not in code:
    code = "import base64\nfrom fastapi.responses import Response\n" + code

# 2. Add signature endpoints and update group_samples
old_group_samples = """@app.get("/api/waiye/group_samples")
async def get_waiye_group_samples(
    group_code: Optional[str] = None,
    township_name: Optional[str] = None,
    village_name: Optional[str] = None,
    group_name: Optional[str] = None
):
    async with SessionLocal() as session:
        if group_code:
            sql = text(\"\"\"
                SELECT id, township_name, village_name, group_name, group_code,
                       cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method
                FROM waiye_samples
                WHERE group_code = :gc
                ORDER BY id
            \"\"\")
            res = await session.execute(sql, {"gc": group_code})
        else:
            sql = text(\"\"\"
                SELECT id, township_name, village_name, group_name, group_code,
                       cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method
                FROM waiye_samples
                WHERE township_name = :tn AND village_name = :vn AND group_name = :gn
                ORDER BY id
            \"\"\")
            res = await session.execute(sql, {"tn": township_name, "vn": village_name, "gn": group_name})
            
        rows = res.fetchall()
        data = []
        for r in rows:
            data.append({
                "id": r[0],
                "township_name": r[1],
                "village_name": r[2],
                "group_name": r[3],
                "group_code": r[4],
                "cbfmc": r[5],
                "cbfbm": r[6],
                "cbfbm_short": r[7],
                "lxdh": r[8],
                "dkmc": r[9],
                "dkbm": r[10],
                "dkbm_short": r[11],
                "scmj": float(r[12]) if r[12] is not None else 0.0,
                "area_acknowledged": r[13] or "",
                "rights_correct": r[14] or "",
                "bound_correct": r[15] or "",
                "member_qualified": r[16] or "",
                "self_verified": r[17] or "",
                "self_signed": r[18] or "",
                "satisfaction": r[19] or "满意",
                "survey_method": r[20] or "现场"
            })
            
        return {"code": 200, "data": data}"""

new_group_samples = """@app.get("/api/waiye/group_samples")
async def get_waiye_group_samples(
    group_code: Optional[str] = None,
    township_name: Optional[str] = None,
    village_name: Optional[str] = None,
    group_name: Optional[str] = None
):
    async with SessionLocal() as session:
        if group_code:
            sql = text(\"\"\"
                SELECT id, township_name, village_name, group_name, group_code,
                       cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method, signature_url
                FROM waiye_samples
                WHERE group_code = :gc
                ORDER BY id
            \"\"\")
            res = await session.execute(sql, {"gc": group_code})
        else:
            sql = text(\"\"\"
                SELECT id, township_name, village_name, group_name, group_code,
                       cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm, dkbm_short, scmj,
                       area_acknowledged, rights_correct, bound_correct, member_qualified,
                       self_verified, self_signed, satisfaction, survey_method, signature_url
                FROM waiye_samples
                WHERE township_name = :tn AND village_name = :vn AND group_name = :gn
                ORDER BY id
            \"\"\")
            res = await session.execute(sql, {"tn": township_name, "vn": village_name, "gn": group_name})
            
        rows = res.fetchall()
        data = []
        sig_dir = os.path.join("uploads", "signatures")
        
        for r in rows:
            cbfbm_val = str(r[6]) if r[6] else ""
            sig_file = os.path.join(sig_dir, f"{cbfbm_val}.png")
            sig_url = ""
            if os.path.exists(sig_file):
                mtime = int(os.path.getmtime(sig_file))
                sig_url = f"/api/signature_image?cbfbm={cbfbm_val}&v={mtime}"
            elif r[21]:
                sig_url = r[21]
                
            data.append({
                "id": r[0],
                "township_name": r[1],
                "village_name": r[2],
                "group_name": r[3],
                "group_code": r[4],
                "cbfmc": r[5],
                "cbfbm": cbfbm_val,
                "cbfbm_short": r[7],
                "lxdh": r[8],
                "dkmc": r[9],
                "dkbm": r[10],
                "dkbm_short": r[11],
                "scmj": float(r[12]) if r[12] is not None else 0.0,
                "area_acknowledged": r[13] or "",
                "rights_correct": r[14] or "",
                "bound_correct": r[15] or "",
                "member_qualified": r[16] or "",
                "self_verified": r[17] or "",
                "self_signed": r[18] or "",
                "satisfaction": r[19] or "满意",
                "survey_method": r[20] or "现场",
                "signature_url": sig_url
            })
            
        return {"code": 200, "data": data}

class SignatureSaveRequest(BaseModel):
    cbfbm: str
    cbfmc: str
    signature_data: str

@app.post("/api/waiye/save_signature")
async def save_waiye_signature(req: SignatureSaveRequest):
    os.makedirs(os.path.join("uploads", "signatures"), exist_ok=True)
    raw_b64 = req.signature_data
    if "," in raw_b64:
        raw_b64 = raw_b64.split(",", 1)[1]
    
    img_bytes = base64.b64decode(raw_b64)
    file_path = os.path.join("uploads", "signatures", f"{req.cbfbm}.png")
    with open(file_path, "wb") as f:
        f.write(img_bytes)
        
    mtime = int(os.path.getmtime(file_path))
    sig_url = f"/api/signature_image?cbfbm={req.cbfbm}&v={mtime}"
    
    async with SessionLocal() as session:
        # 1. Update/insert contractor_signatures
        await session.execute(text(\"\"\"
            INSERT INTO contractor_signatures (cbfbm, cbfmc, signature_path, signature_data, updated_at)
            VALUES (:cbfbm, :cbfmc, :sig_path, :sig_data, CURRENT_TIMESTAMP)
            ON CONFLICT (cbfbm) DO UPDATE SET
                cbfmc = EXCLUDED.cbfmc,
                signature_path = EXCLUDED.signature_path,
                signature_data = EXCLUDED.signature_data,
                updated_at = CURRENT_TIMESTAMP
        \"\"\"), {
            "cbfbm": req.cbfbm,
            "cbfmc": req.cbfmc,
            "sig_path": file_path,
            "sig_data": req.signature_data[:500] # store preview or header
        })
        
        # 2. Update all waiye_samples with this cbfbm
        await session.execute(text(\"\"\"
            UPDATE waiye_samples 
            SET signature_url = :sig_url, updated_at = CURRENT_TIMESTAMP
            WHERE cbfbm = :cbfbm
        \"\"\"), {
            "sig_url": sig_url,
            "cbfbm": req.cbfbm
        })
        await session.commit()
        
    return {
        "code": 200,
        "message": f"【{req.cbfmc}】代表手写签名已保存并关联！",
        "signature_url": sig_url,
        "cbfbm": req.cbfbm
    }

@app.get("/api/signature_image")
async def get_signature_image(cbfbm: str):
    file_path = os.path.join("uploads", "signatures", f"{cbfbm}.png")
    if os.path.exists(file_path):
        from fastapi.responses import FileResponse
        return FileResponse(file_path, media_type="image/png")
    return Response(status_code=404)
"""

code = code.replace(old_group_samples, new_group_samples)

# Ensure api_export_waiye_att8 passes cbfbm
code = code.replace(
    '"cbfmc": r[4],',
    '"cbfmc": r[4],\n                "cbfbm": str(r[0]) if False else (r[0] if False else str(r[0])), # query col 5 is cbfbm'
)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", "w", encoding="utf-8") as f:
    f.write(code)

import py_compile
py_compile.compile(r"G:\全椒县二轮延包\全椒县县级验收管理平台\backend\main.py", doraise=True)
print("main.py signature endpoints added successfully.")