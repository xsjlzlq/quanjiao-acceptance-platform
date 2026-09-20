import os
import shutil
import asyncio
import tempfile
import uuid
import zipfile
from sqlalchemy import text
from database import SessionLocal, parse_qsdwdmb_hierarchy, get_base_dir

from doc_exporter import (
    export_att4, export_att5, export_neiye_att6_township, export_neiye_att6_county,
    export_neiye_att7, export_waiye_att8, export_waiye_att9,
    export_rectify_att12, export_rectify_att13, export_waiye_inquiry, sanitize_filename,
    export_sample_detail_excel, export_neiye_att6_mechanism_only, export_village_meeting_photos
)
from doc_exporter_score import export_att10, export_att11
from score_service import get_all_township_scores, calculate_county_averages
import time

# 全局任务状态管理器
export_tasks = {}

def get_export_task_progress(task_id: str):
    return export_tasks.get(task_id, {
        "status": "not_found",
        "percent": 0,
        "message": "未找到任务",
        "url": None,
        "error": None
    })

def set_export_task_init(task_id: str):
    export_tasks[task_id] = {
        "status": "running",
        "percent": 5,
        "message": "正在准备打包环境与数据...",
        "url": None,
        "error": None,
        "created_at": time.time()
    }

def update_export_task(task_id: str, percent: int, message: str, url: str = None, error: str = None):
    if not task_id:
        return
    if task_id in export_tasks:
        export_tasks[task_id].update({
            "percent": percent,
            "message": message,
            "url": url if url is not None else export_tasks[task_id].get("url"),
            "error": error,
            "status": "failed" if error else ("completed" if percent >= 100 else "running")
        })
    else:
        export_tasks[task_id] = {
            "status": "failed" if error else ("completed" if percent >= 100 else "running"),
            "percent": percent,
            "message": message,
            "url": url,
            "error": error,
            "created_at": time.time()
        }

def make_zip(source_dir, output_filename):
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, source_dir)
                zipf.write(abs_path, rel_path)

async def run_batch_export(level: str, township_code: str, township_name: str, attachments: list, task_id: str = None):
    base_dir = get_base_dir()
    downloads_dir = os.path.join(base_dir, "backend", "downloads")
    
    tmp_uuid = uuid.uuid4().hex
    tmp_dir = os.path.join(tempfile.gettempdir(), f"acceptance_export_{tmp_uuid}")
    os.makedirs(tmp_dir, exist_ok=True)
    
    zip_filename = ""
    if task_id:
        update_export_task(task_id, 8, "正在解析区划层级与数据目标...")
    
    try:
        async with SessionLocal() as session:
            # 动态解析县级信息
            res_h = await session.execute(text("SELECT qsdwdm, qsdwmc FROM qsdwdmb ORDER BY qsdwdm"))
            county_info, _ = parse_qsdwdmb_hierarchy(res_h.fetchall())
            county_code = county_info.get("code", "341124")
            county_name = county_info.get("name", "全椒县")

            if level == "county":
                export_path = os.path.join(tmp_dir, f"{county_name}县级自查验收附件")
                os.makedirs(export_path, exist_ok=True)
                zip_filename = f"{county_name}县级自查验收附件.zip"
                
                # 0. 申请与抽样资料
                if "att5" in attachments or "village_sample_stats" in attachments:
                    sample_dir = os.path.join(export_path, "0.申请与抽样资料")
                    os.makedirs(sample_dir, exist_ok=True)
                    
                    if "att5" in attachments:
                        if task_id:
                            update_export_task(task_id, 15, f"正在汇总生成 附件5 {county_name}自查抽样统计表...")
                        
                        res_all_groups = await session.execute(text("""
                            SELECT DISTINCT township_name, village_name, group_name, group_code
                            FROM waiye_samples
                            WHERE group_code IS NOT NULL AND group_code != ''
                            ORDER BY group_code
                        """))
                        all_sampled_groups = res_all_groups.fetchall()
                        
                        stats_all_rows = []
                        for idx, (t_name, v_name, g_name, g_code) in enumerate(all_sampled_groups, 1):
                            # 统计总户数
                            res_total = await session.execute(text(
                                "SELECT COUNT(DISTINCT cbfbm) FROM cbf WHERE cbfbm::text LIKE :code"
                            ), {"code": f"{g_code}%"})
                            total_cbf = res_total.scalar() or 0

                            # 统计抽样户数
                            res_samp = await session.execute(text(
                                "SELECT COUNT(DISTINCT cbfbm) FROM waiye_samples WHERE group_code = :code"
                            ), {"code": g_code})
                            sampled_cbf = res_samp.scalar() or 0

                            stats_all_rows.append({
                                "序号": idx,
                                "乡镇名称": t_name,
                                "村名称": v_name,
                                "组名称": g_name,
                                "发包方总户数": total_cbf,
                                "抽样农户数5%": sampled_cbf
                            })
                            
                        await asyncio.to_thread(export_att5, stats_all_rows, county_code, county_name)
                        src = os.path.join(downloads_dir, f"附件5_抽样统计表_{county_name}.doc")
                        if os.path.exists(src):
                            shutil.copy(src, os.path.join(sample_dir, f"附件5_抽样统计表_{county_name}.doc"))

                    # 同时生成并归档全县各行政村抽样比例统计表 (.xlsx)
                    if "village_sample_stats" in attachments or "att5" in attachments:
                        try:
                            if task_id:
                                update_export_task(task_id, 20, f"正在汇总生成 {county_name}各行政村抽样比例统计表...")
                            from generate_village_sample_stats import query_village_sample_stats, build_excel
                            v_data = await query_village_sample_stats()
                            v_excel_name = f"{county_name}各行政村抽样比例统计表.xlsx"
                            v_excel_down = os.path.join(downloads_dir, v_excel_name)
                            v_excel_root = os.path.join(base_dir, v_excel_name)
                            v_excel_pkg = os.path.join(sample_dir, v_excel_name)
                            await asyncio.to_thread(build_excel, v_data, [v_excel_down, v_excel_root, v_excel_pkg])
                        except Exception as e_v_excel:
                            print(f"Failed to generate village sample stats excel in batch export: {e_v_excel}")

                # 1. 内业核查资料
                neiye_dir = os.path.join(export_path, "1.内业核查资料")
                os.makedirs(neiye_dir, exist_ok=True)
                
                if "att6_county" in attachments:
                    if task_id:
                        update_export_task(task_id, 30, f"正在生成 附件6 {county_name}县级自查内业组检查记录表...")
                    r1 = await session.execute(text("SELECT form_data FROM neiye_records WHERE qsdwdm = :c_code OR level = 'county'"), {"c_code": county_code})
                    row = r1.fetchone()
                    form_data = row[0] if (row and row[0]) else {}
                    await asyncio.to_thread(export_neiye_att6_county, form_data)
                    src = os.path.join(downloads_dir, f"附件6_{county_name}县级自查内业组检查记录表（1_4）.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(neiye_dir, f"附件6_{county_name}县级自查内业组检查记录表（1_4）.doc"))
                
                if "att7" in attachments:
                    if task_id:
                        update_export_task(task_id, 45, f"正在生成 附件7 {county_name}县级自查内业组检查得分表...")
                    r2 = await session.execute(text("SELECT qsdwdm, qsdwmc, form_data FROM neiye_records"))
                    records_by_qsdwdm = {str(r[0]): {"qsdwmc": r[1], "form_data": r[2] or {}} for r in r2.fetchall()}
                    
                    # 统计各乡镇下抽样村
                    res_sv = await session.execute(text("""
                        SELECT DISTINCT 
                            w.township_name, 
                            SUBSTRING(w.group_code, 1, 12) || '00' as village_code
                        FROM waiye_samples w
                        WHERE w.village_name IS NOT NULL AND w.village_name != ''
                    """))
                    from collections import defaultdict
                    ts_v_map = defaultdict(list)
                    for r in res_sv.fetchall():
                        ts_v_map[r[0]].append(str(r[1]))

                    await asyncio.to_thread(export_neiye_att7, records_by_qsdwdm, dict(ts_v_map))
                    src = os.path.join(downloads_dir, f"附件7_{county_name}县级自查内业组检查得分表.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(neiye_dir, f"附件7_{county_name}县级自查内业组检查得分表.doc"))
                
                # 2. 外业核查资料
                waiye_dir = os.path.join(export_path, "2.外业核查资料")
                os.makedirs(waiye_dir, exist_ok=True)
                
                if "att9" in attachments:
                    if task_id:
                        update_export_task(task_id, 60, f"正在生成 附件9 {county_name}县级自查外业组检查得分表...")
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
                    src = os.path.join(downloads_dir, f"附件9_{county_name}县级自查外业组检查得分表.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(waiye_dir, f"附件9_{county_name}县级自查外业组检查得分表.doc"))
                
                # 3. 验收评定资料
                score_dir = os.path.join(export_path, "3.验收评定资料")
                os.makedirs(score_dir, exist_ok=True)
                
                scores, c_mech, has_county = await get_all_township_scores(session)
                if "att10" in attachments:
                    if task_id:
                        update_export_task(task_id, 75, f"正在生成 附件10 {county_name}县级自查得分汇总表...")
                    await asyncio.to_thread(export_att10, scores, c_mech)
                    src = os.path.join(downloads_dir, f"附件10_{county_name}县级自查得分汇总表.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(score_dir, f"附件10_{county_name}县级自查得分汇总表.doc"))
                
                if "att11" in attachments:
                    if task_id:
                        update_export_task(task_id, 85, f"正在生成 附件11 {county_name}县级自查验收评定表...")
                    # 获取特殊扣分项
                    special1, special2, special3 = False, False, 0.0
                    r_spec = await session.execute(text("SELECT form_data FROM neiye_records WHERE qsdwdm = :c_code OR level = 'county'"), {"c_code": county_code})
                    s_row = r_spec.fetchone()
                    if s_row and s_row[0]:
                        s_fd = s_row[0]
                        special1 = s_fd.get("special1", False)
                        special2 = s_fd.get("special2", False)
                        special3 = s_fd.get("special3", 0.0)
                        
                    county_avg = calculate_county_averages(scores, c_mech, has_county)
                    deduct = (0.5 if special1 else 0.0) + (1.0 if special2 else 0.0) + special3
                    final_score = county_avg["mech"] + county_avg["prog_nei"] + county_avg["policy"] + county_avg["effect_nei"] + county_avg["prog_wai"] + county_avg["effect_wai"] - deduct
                    final_score = max(round(final_score, 1), 0.0)
                    
                    await asyncio.to_thread(export_att11, county_avg, special1, special2, special3, final_score)
                    src = os.path.join(downloads_dir, f"附件11_{county_name}县级自查验收评定表.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(score_dir, f"附件11_{county_name}县级自查验收评定表.doc"))
                        
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
                    if task_id:
                        update_export_task(task_id, 12, f"正在汇总 {township_name} 抽样统计数据...")
                    res_groups = await session.execute(text("""
                        SELECT DISTINCT group_code, group_name, village_name
                        FROM waiye_samples
                        WHERE township_name = :name
                        ORDER BY group_code
                    """), {"name": township_name})
                    groups = res_groups.fetchall()

                    for idx, (g_code, g_name, v_name) in enumerate(groups, 1):
                        # 1. 准确统计该发包方（村民小组）在承包方表中的总户数
                        res_total = await session.execute(text(
                            "SELECT COUNT(DISTINCT cbfbm) FROM cbf WHERE cbfbm::text LIKE :code"
                        ), {"code": f"{g_code}%"})
                        total_cbf = res_total.scalar() or 0

                        # 2. 准确统计外业抽样表中该发包方实际抽取的去重承包方农户数
                        res_samp = await session.execute(text(
                            "SELECT COUNT(DISTINCT cbfbm) FROM waiye_samples WHERE group_code = :code"
                        ), {"code": g_code})
                        sampled_cbf = res_samp.scalar() or 0

                        stats_rows.append({
                            "序号": idx,
                            "乡镇名称": township_name,
                            "村名称": v_name,
                            "组名称": g_name,
                            "发包方总户数": total_cbf,
                            "抽样农户数5%": sampled_cbf
                        })
                            
                if "att4" in attachments:
                    if task_id:
                        update_export_task(task_id, 18, f"正在生成 附件4 成果检查验收申请表 ({township_name})...")
                    farmer_count = sum(r["发包方总户数"] for r in stats_rows)
                    r_area = await session.execute(text("SELECT SUM(htmjm) FROM cbdkxx WHERE cbfbm::text LIKE :code"), {"code": f"{township_code}%"})
                    total_area = (r_area.fetchone()[0] or 0.0)
                    await asyncio.to_thread(export_att4, township_name, farmer_count, total_area)
                    src = os.path.join(downloads_dir, f"附件4_成果检查验收申请表_{clean_ts}.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(apply_dir, f"附件4_成果检查验收申请表_{clean_ts}.doc"))
                        
                if "att5" in attachments:
                    if task_id:
                        update_export_task(task_id, 24, f"正在生成 附件5 抽样统计表 ({township_name})...")
                    await asyncio.to_thread(export_att5, stats_rows, township_code, township_name)
                    src = os.path.join(downloads_dir, f"附件5_抽样统计表_{clean_ts}.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(apply_dir, f"附件5_抽样统计表_{clean_ts}.doc"))

                if "sample_detail_excel" in attachments:
                    if task_id:
                        update_export_task(task_id, 27, f"正在生成 自查抽样明细表.xlsx ({township_name})...")
                    r_cbf_detail = await session.execute(text("""
                        SELECT DISTINCT
                            w.township_name,
                            w.village_name,
                            w.group_name,
                            w.cbfbm,
                            w.cbfmc,
                            COALESCE(c.cbfzjhm, '') as cbfzjhm
                        FROM waiye_samples w
                        LEFT JOIN cbf c ON w.cbfbm::text = c.cbfbm::text
                        WHERE w.township_name = :name
                        ORDER BY w.village_name, w.group_name, w.cbfbm
                    """), {"name": township_name})
                    cbf_detail_rows = [dict(zip(r_cbf_detail.keys(), r)) for r in r_cbf_detail.fetchall()]
                    await asyncio.to_thread(export_sample_detail_excel, township_name, cbf_detail_rows)
                    src = os.path.join(downloads_dir, f"自查抽样明细表_{clean_ts}.xlsx")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(apply_dir, f"自查抽样明细表_{clean_ts}.xlsx"))
                
                # 2. 内业核查
                neiye_dir = os.path.join(export_path, "2.内业核查")
                os.makedirs(neiye_dir, exist_ok=True)
                if "att6_township" in attachments:
                    # 2.1 导出乡镇本级附件6（同县级仅导出机制运行 1/4，映射为 XX县XX镇）
                    if task_id:
                        update_export_task(task_id, 30, f"正在生成 附件6 检查记录表 ({township_name} 乡镇机制运行 1/4)...")
                    r_ts = await session.execute(text("SELECT form_data FROM neiye_records WHERE qsdwdm = :code"), {"code": township_code})
                    row_ts = r_ts.fetchone()
                    fd_ts = row_ts[0] if (row_ts and row_ts[0]) else {}
                    await asyncio.to_thread(export_neiye_att6_mechanism_only, fd_ts, False, township_name)
                    src_ts = os.path.join(downloads_dir, f"附件6_{county_name}县级自查内业组检查记录表_{clean_ts}（1_4）.doc")
                    if os.path.exists(src_ts):
                        shutil.copy(src_ts, os.path.join(neiye_dir, f"附件6_{county_name}县级自查内业组检查记录表_{clean_ts}（1_4）.doc"))

                    # 2.2 导出该镇下所有抽样村的附件6检查记录表（映射为 XX县XX镇XX村）
                    r_villages = await session.execute(text("""
                        SELECT DISTINCT 
                            w.village_name, 
                            SUBSTRING(w.group_code, 1, 12) || '00' as village_code
                        FROM waiye_samples w
                        WHERE w.township_name = :name AND w.village_name IS NOT NULL AND w.village_name != ''
                    """), {"name": township_name})
                    v_list = r_villages.fetchall()
                    if v_list:
                        total_v = len(v_list)
                        for v_i, (vn, vc) in enumerate(v_list, 1):
                            if task_id:
                                cur_pct = 32 + int(8 * v_i / max(total_v, 1))
                                update_export_task(task_id, cur_pct, f"正在生成 附件6 检查记录表 ({township_name} - {vn}, {v_i}/{total_v})...")
                            rv = await session.execute(text("SELECT form_data FROM neiye_records WHERE qsdwdm = :code"), {"code": str(vc)})
                            row_v = rv.fetchone()
                            fd_v = row_v[0] if (row_v and row_v[0]) else {}
                            await asyncio.to_thread(export_neiye_att6_township, f"{township_name} - {vn}", fd_v, township_name, vn)
                            clean_target = sanitize_filename(f"{township_name} - {vn}")
                            src = os.path.join(downloads_dir, f"附件6_{county_name}县级自查内业组检查记录表_{clean_target}.doc")
                            if os.path.exists(src):
                                shutil.copy(src, os.path.join(neiye_dir, f"附件6_{county_name}县级自查内业组检查记录表_{clean_target}.doc"))
                
                # 3. 外业核查
                waiye_dir = os.path.join(export_path, "3.外业核查")
                os.makedirs(waiye_dir, exist_ok=True)
                
                waiye_rows = []
                if "att8" in attachments or "att13" in attachments or "inquiry" in attachments:
                    if task_id:
                        update_export_task(task_id, 42, f"正在读取 {township_name} 外业核查底表数据...")
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
                    
                    total_g = len(groups)
                    for g_i, ((v_name, g_name), g_rows) in enumerate(groups.items(), 1):
                        if task_id:
                            cur_pct = 45 + int(35 * g_i / max(total_g, 1))
                            update_export_task(task_id, cur_pct, f"正在生成 附件8 外业核查记录表 ({v_name} - {g_name}, {g_i}/{total_g}, 共 {len(g_rows)} 宗地块)...")
                        await asyncio.to_thread(export_waiye_att8, township_name, v_name, g_name, g_rows)
                        clean_vn = sanitize_filename(v_name)
                        clean_gn = sanitize_filename(g_name)
                        src = os.path.join(downloads_dir, f"附件8_外业核查记录表_{clean_ts}{clean_vn}{clean_gn}.doc")
                        if os.path.exists(src):
                            shutil.copy(src, os.path.join(waiye_dir, f"附件8_外业核查记录表_{clean_ts}{clean_vn}{clean_gn}.doc"))
                
                if "inquiry" in attachments:
                    inquiry_dir = os.path.join(waiye_dir, "询问笔录")
                    os.makedirs(inquiry_dir, exist_ok=True)
                    
                    # 仅限真实农户的问询笔录全量导出，严格排除村级现场会伪记录 (cbfbm 以 VILLAGE_ 开头或 cbfmc 为“行政村现场会”)
                    r_inq = await session.execute(text("""
                        SELECT i.cbfbm, i.form_data, i.village_name, i.group_name, i.cbfmc, COALESCE(c.lxdh, '')
                        FROM waiye_inquiries i
                        LEFT JOIN cbf c ON i.cbfbm::text = c.cbfbm::text
                        WHERE i.township_name = :name
                          AND i.cbfbm NOT LIKE 'VILLAGE_%'
                          AND i.cbfmc != '行政村现场会'
                        ORDER BY i.village_name, i.group_name, i.cbfbm
                    """), {"name": township_name})
                    inq_rows = r_inq.fetchall()
                    total_inq = len(inq_rows)
                    
                    for inq_i, i_row in enumerate(inq_rows, 1):
                        cbfbm, fd, village_name, group_name, cbfmc, lxdh = i_row
                        if task_id:
                            cur_pct = 82 + int(10 * inq_i / max(total_inq, 1))
                            update_export_task(task_id, cur_pct, f"正在生成 询问笔录 ({cbfmc}, {inq_i}/{total_inq})...")
                        fd = fd or {}
                        bxwr_name = fd.get("bxwr") or fd.get("cbfmc") or cbfmc
                        photos = fd.get("photos") or []
                        data = {
                            "cbfbm": cbfbm, 
                            "cbfmc": cbfmc,
                            "bxwr": bxwr_name,
                            "township_name": township_name, "village_name": village_name, "group_name": group_name,
                            "lxdh": fd.get("lxdh", lxdh), "gender": fd.get("gender", "男"),
                            "form_data": fd,
                            "photos": photos
                        }
                        inq_url = await asyncio.to_thread(export_waiye_inquiry, data)
                        if inq_url and "file=" in inq_url:
                            rel_doc = inq_url.split("file=")[-1]
                            doc_name = os.path.basename(rel_doc)
                            src = os.path.join(base_dir, "backend", rel_doc)
                            if not os.path.exists(src):
                                src = os.path.join(base_dir, rel_doc)
                            if os.path.exists(src):
                                shutil.copy(src, os.path.join(inquiry_dir, doc_name))

                # 3.2 导出现场会照片（XX镇现场会照片/XX镇XX村现场会照片.docx）
                if "village_meeting_photos" in attachments:
                    photo_folder_name = f"{clean_ts}现场会照片"
                    photo_dir = os.path.join(waiye_dir, photo_folder_name)
                    os.makedirs(photo_dir, exist_ok=True)

                    # 查询该镇所有抽样的行政村列表
                    r_p_villages = await session.execute(text("""
                        SELECT DISTINCT 
                            village_name, 
                            SUBSTRING(group_code, 1, 12) || '00' as village_code
                        FROM waiye_samples
                        WHERE township_name = :name AND village_name IS NOT NULL AND village_name != ''
                        ORDER BY village_name
                    """), {"name": township_name})
                    p_v_list = r_p_villages.fetchall()
                    total_pv = len(p_v_list)

                    for pv_i, (p_vn, p_vc) in enumerate(p_v_list, 1):
                        if task_id:
                            cur_pct = 90 + int(3 * pv_i / max(total_pv, 1))
                            update_export_task(task_id, cur_pct, f"正在生成现场会照片文档 ({township_name} - {p_vn}, {pv_i}/{total_pv})...")

                        # 从 waiye_inquiries 获取村级现场会照片
                        v_target = f"VILLAGE_{str(p_vc).strip()}"
                        rv_photo = await session.execute(
                            text("SELECT form_data FROM waiye_inquiries WHERE cbfbm = :t LIMIT 1"),
                            {"t": v_target}
                        )
                        r_row = rv_photo.fetchone()
                        v_photos = []
                        if r_row and r_row[0]:
                            v_photos = r_row[0].get("photos") or []

                        doc_url = await asyncio.to_thread(export_village_meeting_photos, township_name, p_vn, v_photos)
                        if doc_url and "file=" in doc_url:
                            rel_doc = doc_url.split("file=")[-1]
                            doc_name = os.path.basename(rel_doc)
                            src = os.path.join(base_dir, "backend", rel_doc)
                            if not os.path.exists(src):
                                src = os.path.join(base_dir, rel_doc)
                            if os.path.exists(src):
                                shutil.copy(src, os.path.join(photo_dir, doc_name))

                # 4. 问题整改
                rectify_dir = os.path.join(export_path, "4.问题整改")
                os.makedirs(rectify_dir, exist_ok=True)
                
                if "att12" in attachments:
                    if task_id:
                        update_export_task(task_id, 93, f"正在生成 附件12 整改通知书 ({township_name})...")
                    await asyncio.to_thread(export_rectify_att12, township_name)
                    src = os.path.join(downloads_dir, f"附件12_整改通知书_{clean_ts}.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(rectify_dir, f"附件12_整改通知书_{clean_ts}.doc"))
                        
                if "att13" in attachments:
                    if task_id:
                        update_export_task(task_id, 96, f"正在生成 附件13 问题整改销号台账 ({township_name})...")
                    r1 = await session.execute(text("SELECT form_data FROM neiye_records WHERE qsdwdm = :code"), {"code": township_code})
                    row = r1.fetchone()
                    neiye_form = row[0] if (row and row[0]) else {}
                    await asyncio.to_thread(export_rectify_att13, township_name, neiye_form, waiye_rows)
                    src = os.path.join(downloads_dir, f"附件13_问题整改销号台账_{clean_ts}.doc")
                    if os.path.exists(src):
                        shutil.copy(src, os.path.join(rectify_dir, f"附件13_问题整改销号台账_{clean_ts}.doc"))
        
        # Zip it
        if task_id:
            update_export_task(task_id, 98, "正在压缩归档所有 Word 附件文件...")
        zip_output_path = os.path.join(downloads_dir, f"{tmp_uuid}_{zip_filename}")
        await asyncio.to_thread(make_zip, export_path, zip_output_path)
        
        final_url = f"/api/download?file=downloads/{tmp_uuid}_{zip_filename}"
        if task_id:
            update_export_task(task_id, 100, "批量打包全部完成！正在准备下载...", url=final_url)

        return final_url
        
    except Exception as e:
        print("run_batch_export error:", e)
        if task_id:
            update_export_task(task_id, 100, f"打包失败: {str(e)}", error=str(e))
        return None
        
    except Exception as e:
        print("run_batch_export error:", e)
        return None
    finally:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except:
            pass
