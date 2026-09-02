import os
import shutil
import asyncio
import tempfile
import uuid
import zipfile
from sqlalchemy import text
from database import SessionLocal

from doc_exporter import (
    export_att4, export_att5, export_neiye_att6_township, export_neiye_att6_county,
    export_neiye_att7, export_waiye_att8, export_waiye_att9,
    export_rectify_att12, export_rectify_att13, export_waiye_inquiry, sanitize_filename
)
from doc_exporter_score import export_att10, export_att11
from score_service import get_all_township_scores

def make_zip(source_dir, output_filename):
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, source_dir)
                zipf.write(abs_path, rel_path)

async def run_batch_export(level: str, township_code: str, township_name: str, attachments: list):
    base_dir = os.path.abspath(r"G:\全椒县二轮延包\全椒县县级验收管理平台")
    downloads_dir = os.path.join(base_dir, "backend", "downloads")
    
    tmp_uuid = uuid.uuid4().hex
    tmp_dir = os.path.join(tempfile.gettempdir(), f"quanjiao_export_{tmp_uuid}")
    os.makedirs(tmp_dir, exist_ok=True)
    
    zip_filename = ""
    
    try:
        async with SessionLocal() as session:
            if level == "county":
                export_path = os.path.join(tmp_dir, "全椒县县级自查验收附件")
                os.makedirs(export_path, exist_ok=True)
                zip_filename = "全椒县县级自查验收附件.zip"
                
                # 1. 内业核查资料
                neiye_dir = os.path.join(export_path, "1.内业核查资料")
                os.makedirs(neiye_dir, exist_ok=True)
                
                if "att6_county" in attachments:
                    r1 = await session.execute(text("SELECT form_data FROM neiye_records WHERE qsdwdm = '341124'"))
                    row = r1.fetchone()
                    form_data = row[0] if (row and row[0]) else {}
                    await asyncio.to_thread(export_neiye_att6_county, form_data)
                    src = os.path.join(downloads_dir, "附件6_全椒县县级自查内业组检查记录表（1_4）.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(neiye_dir, "附件6_全椒县县级自查内业组检查记录表（1_4）.doc"))
                
                if "att7" in attachments:
                    r2 = await session.execute(text("SELECT qsdwdm, qsdwmc, form_data FROM neiye_records"))
                    records_by_qsdwdm = {str(r[0]): {"qsdwmc": r[1], "form_data": r[2] or {}} for r in r2.fetchall()}
                    await asyncio.to_thread(export_neiye_att7, records_by_qsdwdm)
                    src = os.path.join(downloads_dir, "附件7_全椒县县级自查内业组检查得分表.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(neiye_dir, "附件7_全椒县县级自查内业组检查得分表.doc"))
                
                # 2. 外业核查资料
                waiye_dir = os.path.join(export_path, "2.外业核查资料")
                os.makedirs(waiye_dir, exist_ok=True)
                
                if "att9" in attachments:
                    r3 = await session.execute(text("""
                        SELECT id, township_name, village_name, group_name,
                               cbfmc, cbfbm, cbfbm_short, lxdh, dkmc, dkbm_short, scmj,
                               area_acknowledged, rights_correct, bound_correct, member_qualified,
                               self_verified, self_signed, satisfaction, survey_method, signature_url, phone_correct
                        FROM waiye_samples
                        ORDER BY township_name, village_name, group_name, cbfbm, id
                    """))
                    samples_rows = [dict(zip(r3.keys(), r)) for r in r3.fetchall()]
                    await asyncio.to_thread(export_waiye_att9, samples_rows)
                    src = os.path.join(downloads_dir, "附件9_全椒县县级自查外业组检查得分表.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(waiye_dir, "附件9_全椒县县级自查外业组检查得分表.doc"))
                
                # 3. 验收评定资料
                score_dir = os.path.join(export_path, "3.验收评定资料")
                os.makedirs(score_dir, exist_ok=True)
                
                scores, c_mech, has_county = await get_all_township_scores(session)
                if "att10" in attachments:
                    await asyncio.to_thread(export_att10, scores, c_mech)
                    src = os.path.join(downloads_dir, "附件10_全椒县县级自查得分汇总表.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(score_dir, "附件10_全椒县县级自查得分汇总表.doc"))
                
                if "att11" in attachments:
                    # 获取特殊扣分项
                    special1, special2, special3 = False, False, 0.0
                    r_spec = await session.execute(text("SELECT form_data FROM neiye_records WHERE qsdwdm = '341124'"))
                    s_row = r_spec.fetchone()
                    if s_row and s_row[0]:
                        s_fd = s_row[0]
                        special1 = s_fd.get("special1", False)
                        special2 = s_fd.get("special2", False)
                        special3 = s_fd.get("special3", 0.0)
                        
                    county_mech = 15.0
                    county_prog_nei = 30.0
                    county_policy = 15.0
                    county_effect_nei = 10.0
                    county_prog_wai = 20.0
                    county_effect_wai = 10.0
                    
                    if len(scores) > 0:
                        mech_sum = sum(s["mech"] for s in scores.values())
                        if has_county:
                            county_mech = (mech_sum + c_mech) / (len(scores) + 1)
                        else:
                            county_mech = mech_sum / len(scores)
                            
                        county_prog_nei = sum(s["prog_nei"] for s in scores.values()) / len(scores)
                        county_policy = sum(s["policy"] for s in scores.values()) / len(scores)
                        county_effect_nei = sum(s["effect_nei"] for s in scores.values()) / len(scores)
                        county_prog_wai = sum(s["prog_wai"] for s in scores.values()) / len(scores)
                        county_effect_wai = sum(s["effect_wai"] for s in scores.values()) / len(scores)
                        
                    county_avg = {
                        "mech": county_mech, "prog_nei": county_prog_nei, "policy": county_policy,
                        "effect_nei": county_effect_nei, "prog_wai": county_prog_wai, "effect_wai": county_effect_wai
                    }
                    deduct = (0.5 if special1 else 0.0) + (1.0 if special2 else 0.0) + special3
                    final_score = round(county_mech, 1) + round(county_prog_nei, 1) + round(county_policy, 1) + round(county_effect_nei, 1) + round(county_prog_wai, 1) + round(county_effect_wai, 1) - deduct
                    final_score = max(final_score, 0.0)
                    
                    await asyncio.to_thread(export_att11, county_avg, special1, special2, special3, final_score)
                    src = os.path.join(downloads_dir, "附件11_全椒县县级自查验收评定表.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(score_dir, "附件11_全椒县县级自查验收评定表.doc"))
                        
            elif level == "township":
                clean_ts = sanitize_filename(township_name)
                export_path = os.path.join(tmp_dir, f"{clean_ts}_验收附件")
                os.makedirs(export_path, exist_ok=True)
                zip_filename = f"{clean_ts}_验收附件.zip"
                
                # 1. 申请与抽样
                apply_dir = os.path.join(export_path, "1.申请与抽样")
                os.makedirs(apply_dir, exist_ok=True)
                
                # For att4, att5 we need stats
                stats_rows = []
                if "att4" in attachments or "att5" in attachments:
                    v_res = await session.execute(text("SELECT qsdwdm, qsdwmc FROM qsdwdmb WHERE qsdwdm::text LIKE :code"), {"code": f"{township_code}%"})
                    v_dict = {str(r[0]): r[1] for r in v_res.fetchall()}
                    from collections import defaultdict
                    group_map = defaultdict(lambda: {"total": 0, "sampled": 0})
                    
                    # Fetch total contractors
                    r_cbf = await session.execute(text("SELECT cbfbm FROM cbf WHERE cbfbm::text LIKE :code"), {"code": f"{township_code}%"})
                    for (c_bm,) in r_cbf.fetchall():
                        c_str = str(c_bm)
                        if len(c_str) >= 14:
                            g_code = c_str[:14]
                            group_map[g_code]["total"] += 1
                    
                    # Fetch sampled
                    r_samp = await session.execute(text("SELECT cbfbm FROM waiye_samples WHERE township_name = :name"), {"name": township_name})
                    for (c_bm,) in r_samp.fetchall():
                        c_str = str(c_bm)
                        if len(c_str) >= 14:
                            g_code = c_str[:14]
                            group_map[g_code]["sampled"] += 1
                            
                    idx = 1
                    for g_code, counts in group_map.items():
                        v_code = g_code[:12] + "00"
                        v_name = v_dict.get(v_code, "未知村")
                        g_name = v_dict.get(g_code, "未知组")
                        if counts["sampled"] > 0:
                            stats_rows.append({
                                "序号": idx, "乡镇名称": township_name, "村名称": v_name, "组名称": g_name,
                                "发包方总户数": counts["total"], "抽样农户数5%": counts["sampled"]
                            })
                            idx += 1
                            
                if "att4" in attachments:
                    farmer_count = sum(r["发包方总户数"] for r in stats_rows)
                    r_area = await session.execute(text("SELECT SUM(htmjm) FROM cbdkxx WHERE cbfbm::text LIKE :code"), {"code": f"{township_code}%"})
                    total_area = (r_area.fetchone()[0] or 0.0)
                    await asyncio.to_thread(export_att4, township_name, farmer_count, total_area)
                    src = os.path.join(downloads_dir, f"附件4_成果检查验收申请表_{clean_ts}.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(apply_dir, f"附件4_成果检查验收申请表_{clean_ts}.doc"))
                        
                if "att5" in attachments:
                    await asyncio.to_thread(export_att5, stats_rows, township_code, township_name)
                    src = os.path.join(downloads_dir, f"附件5_抽样统计表_{clean_ts}.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(apply_dir, f"附件5_抽样统计表_{clean_ts}.doc"))
                
                # 2. 内业核查
                neiye_dir = os.path.join(export_path, "2.内业核查")
                os.makedirs(neiye_dir, exist_ok=True)
                if "att6_township" in attachments:
                    r1 = await session.execute(text("SELECT form_data FROM neiye_records WHERE qsdwdm = :code"), {"code": township_code})
                    row = r1.fetchone()
                    form_data = row[0] if (row and row[0]) else {}
                    await asyncio.to_thread(export_neiye_att6_township, township_name, form_data)
                    src = os.path.join(downloads_dir, f"附件6_全椒县县级自查内业组检查记录表_{clean_ts}.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(neiye_dir, f"附件6_全椒县县级自查内业组检查记录表_{clean_ts}.doc"))
                
                # 3. 外业核查
                waiye_dir = os.path.join(export_path, "3.外业核查")
                os.makedirs(waiye_dir, exist_ok=True)
                
                waiye_rows = []
                if "att8" in attachments or "att13" in attachments or "inquiry" in attachments:
                    r_waiye = await session.execute(text("""
                        SELECT village_name, group_name, cbfmc,
                               area_acknowledged, rights_correct, bound_correct,
                               member_qualified, self_verified, self_signed, phone_correct,
                               cbfbm_short, dkbm_short, dkmc,
                               survey_method, satisfaction, lxdh, cbfbm
                        FROM waiye_samples WHERE township_name = :name
                        ORDER BY village_name, group_name, cbfbm
                    """), {"name": township_name})
                    waiye_rows = [dict(zip(r_waiye.keys(), r)) for r in r_waiye.fetchall()]
                    
                if "att8" in attachments:
                    from collections import defaultdict
                    groups = defaultdict(list)
                    for r in waiye_rows:
                        groups[(r['village_name'], r['group_name'])].append(r)
                    
                    for (v_name, g_name), g_rows in groups.items():
                        await asyncio.to_thread(export_waiye_att8, township_name, v_name, g_name, g_rows)
                        clean_vn = sanitize_filename(v_name)
                        clean_gn = sanitize_filename(g_name)
                        src = os.path.join(downloads_dir, f"附件8_外业核查记录表_{clean_ts}{clean_vn}{clean_gn}.doc")
                        if os.path.exists(src):
                            shutil.copy(src, os.path.join(waiye_dir, f"附件8_外业核查记录表_{clean_ts}{clean_vn}{clean_gn}.doc"))
                
                if "inquiry" in attachments:
                    inquiry_dir = os.path.join(waiye_dir, "询问笔录")
                    os.makedirs(inquiry_dir, exist_ok=True)
                    
                    r_inq = await session.execute(text("""
                        SELECT i.cbfbm, i.form_data, w.village_name, w.group_name, w.cbfmc, c.lxdh
                        FROM waiye_inquiries i
                        JOIN (SELECT DISTINCT cbfbm, village_name, group_name, cbfmc FROM waiye_samples WHERE township_name = :name) w ON i.cbfbm = w.cbfbm
                        LEFT JOIN cbf c ON i.cbfbm = c.cbfbm
                    """), {"name": township_name})
                    
                    for i_row in r_inq.fetchall():
                        cbfbm, fd, village_name, group_name, cbfmc, lxdh = i_row
                        data = {
                            "cbfbm": cbfbm, "cbfmc": fd.get("cbfmc", cbfmc),
                            "township_name": township_name, "village_name": village_name, "group_name": group_name,
                            "lxdh": fd.get("lxdh", lxdh), "gender": fd.get("gender", "男"),
                            "form_data": fd or {}
                        }
                        await asyncio.to_thread(export_waiye_inquiry, data)
                        clean_cbf = sanitize_filename(data["cbfmc"])
                        src = os.path.join(downloads_dir, f"附件_询问笔录_{clean_cbf}.doc")
                        if os.path.exists(src):
                            shutil.copy(src, os.path.join(inquiry_dir, f"附件_询问笔录_{clean_cbf}.doc"))

                # 4. 问题整改
                rectify_dir = os.path.join(export_path, "4.问题整改")
                os.makedirs(rectify_dir, exist_ok=True)
                
                if "att12" in attachments:
                    await asyncio.to_thread(export_rectify_att12, township_name)
                    src = os.path.join(downloads_dir, f"附件12_整改通知书_{clean_ts}.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(rectify_dir, f"附件12_整改通知书_{clean_ts}.doc"))
                        
                if "att13" in attachments:
                    r1 = await session.execute(text("SELECT form_data FROM neiye_records WHERE qsdwdm = :code"), {"code": township_code})
                    row = r1.fetchone()
                    neiye_form = row[0] if (row and row[0]) else {}
                    await asyncio.to_thread(export_rectify_att13, township_name, neiye_form, waiye_rows)
                    src = os.path.join(downloads_dir, f"附件13_问题整改销号台账_{clean_ts}.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(rectify_dir, f"附件13_问题整改销号台账_{clean_ts}.doc"))
        
        # Zip it
        zip_output_path = os.path.join(downloads_dir, f"{tmp_uuid}_{zip_filename}")
        await asyncio.to_thread(make_zip, export_path, zip_output_path)
        
        return f"/api/download?file=downloads/{tmp_uuid}_{zip_filename}"
        
    except Exception as e:
        print("run_batch_export error:", e)
        return None
    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except:
            pass
