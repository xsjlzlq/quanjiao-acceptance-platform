from sqlalchemy import text
from collections import defaultdict
from doc_exporter import calculate_neiye_subscores
from database import parse_qsdwdmb_hierarchy

async def get_all_township_scores(session):
    # 动态从 qsdwdmb 解析县级代码与有效乡镇列表
    try:
        res_h = await session.execute(text("SELECT qsdwdm, qsdwmc FROM qsdwdmb ORDER BY qsdwdm"))
        rows_h = res_h.fetchall()
        county_info, township_list = parse_qsdwdmb_hierarchy(rows_h)
        county_code = county_info["code"] if county_info else "341124"
        valid_names = set(t["name"] for t in township_list)
    except Exception as e:
        print(f"[score_service] 解析 qsdwdmb 异常: {e}")
        county_code = "341124"
        valid_names = set()

    # Get Neiye
    res_nei = await session.execute(text("SELECT qsdwdm, qsdwmc, form_data, level FROM neiye_records"))
    nei_rows = res_nei.fetchall()
    
    township_scores = {}
    county_mech = 15.0
    has_county = False
    
    for r in nei_rows:
        q_dm, q_mc, fd, lvl = r[0], r[1], r[2] or {}, r[3]
        scores = calculate_neiye_subscores(fd)["score"]
        if q_dm == county_code or lvl == 'county':
            county_mech = scores["mech"]
            has_county = True
        else:
            if not valid_names or q_mc in valid_names:
                township_scores[q_mc] = {
                    "mech": scores["mech"],
                    "prog_nei": scores["prog"],
                    "policy": scores["policy"],
                    "effect_nei": scores["effect"],
                    "prog_wai": 20.0,
                    "effect_wai": 10.0
                }
        
    # Get Waiye (计算规则：村得分由各组得分平均值，乡镇得分为各村平均值)
    res_wai = await session.execute(text("""
        SELECT township_name, village_name, group_code, 
               SUM(CASE WHEN area_acknowledged='X' THEN 1 ELSE 0 END +
                   CASE WHEN rights_correct='X' THEN 1 ELSE 0 END +
                   CASE WHEN bound_correct='X' THEN 1 ELSE 0 END +
                   CASE WHEN member_qualified='X' THEN 1 ELSE 0 END +
                   CASE WHEN self_verified='X' THEN 1 ELSE 0 END +
                   CASE WHEN self_signed='X' THEN 1 ELSE 0 END) as errors,
               SUM(CASE WHEN satisfaction='满意' THEN 1 ELSE 0 END) as sats,
               COUNT(*) as total
        FROM waiye_samples
        GROUP BY township_name, village_name, group_code
    """))
    wai_rows = res_wai.fetchall()
    
    wai_hierarchy = defaultdict(lambda: defaultdict(list))
    for r in wai_rows:
        t_name, v_name, g_code, errors, sats, total = r
        if total > 0:
            prog = max(20.0 - float(errors) * 0.5, 0.0)
            eff = (float(sats) / total * 10.0)
            wai_hierarchy[t_name][v_name].append((prog, eff))
            
    for t_name, v_map in wai_hierarchy.items():
        if valid_names and t_name not in valid_names:
            continue
        v_scores = []
        for v_name, sc_list in v_map.items():
            if sc_list:
                # 村得分由各组得分平均值
                v_prog = sum(x[0] for x in sc_list) / len(sc_list)
                v_eff = sum(x[1] for x in sc_list) / len(sc_list)
                v_scores.append((v_prog, v_eff))
                
        if v_scores:
            # 乡镇得分为各村平均值
            avg_prog = sum(x[0] for x in v_scores) / len(v_scores)
            avg_eff = sum(x[1] for x in v_scores) / len(v_scores)
        else:
            avg_prog = 20.0
            avg_eff = 10.0

        if t_name not in township_scores:
            township_scores[t_name] = {
                "mech": 15.0, "prog_nei": 30.0, "policy": 15.0, "effect_nei": 10.0,
                "prog_wai": avg_prog, "effect_wai": avg_eff
            }
        else:
            township_scores[t_name]["prog_wai"] = avg_prog
            township_scores[t_name]["effect_wai"] = avg_eff
            
    for t_name, sc in township_scores.items():
        sc["total"] = round(round(sc["mech"], 1) + round(sc["prog_nei"], 1) + round(sc["prog_wai"], 1) + round(sc["policy"], 1) + round(sc["effect_nei"], 1) + round(sc["effect_wai"], 1), 1)
        
    return township_scores, county_mech, has_county
