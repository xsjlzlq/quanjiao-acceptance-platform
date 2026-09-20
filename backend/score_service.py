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

    # 获取乡镇与抽样村代码的归属关系
    res_sampled_v = await session.execute(text("""
        SELECT DISTINCT 
            w.township_name, 
            SUBSTRING(w.group_code, 1, 12) || '00' as village_code
        FROM waiye_samples w
        WHERE w.village_name IS NOT NULL AND w.village_name != ''
    """))
    ts_v_map = defaultdict(list)
    for r in res_sampled_v.fetchall():
        ts_v_map[r[0]].append(str(r[1]))

    # Get Neiye
    res_nei = await session.execute(text("SELECT qsdwdm, qsdwmc, form_data, level FROM neiye_records"))
    nei_rows = res_nei.fetchall()
    
    township_scores = {}
    county_mech = 15.0
    has_county = False
    
    # 将内业记录按代码建立索引
    records_dict = {}
    for r in nei_rows:
        q_dm, q_mc, fd, lvl = str(r[0]), r[1], r[2] or {}, r[3]
        scores = calculate_neiye_subscores(fd)["score"]
        records_dict[q_dm] = scores
        if q_dm == county_code or lvl == 'county':
            county_mech = scores["mech"]
            has_county = True

    # 按照各乡镇下抽样村与乡镇本级的得分计算平均分
    for t_item in township_list:
        t_name = t_item["name"]
        t_code = t_item["code"]
        v_codes = ts_v_map.get(t_name, [])
        
        # 获取该乡镇自身的机制运行得分 (qsdwdm == t_code)
        township_self_mech = records_dict.get(t_code, {}).get("mech")

        village_scores = []
        if v_codes:
            for vc in v_codes:
                if vc in records_dict:
                    village_scores.append(records_dict[vc])
        else:
            # 兼容：查询以此镇代码开头的内业村级或镇级记录
            for r_code, sc in records_dict.items():
                if r_code != county_code and (r_code == t_code or (r_code.startswith(t_code) and len(r_code) > 9)):
                    village_scores.append(sc)

        has_neiye = bool(village_scores) or (township_self_mech is not None)
        if village_scores:
            k = len(village_scores)
            village_avg_mech = sum(s["mech"] for s in village_scores) / k
            avg_pn = sum(s["prog"] for s in village_scores) / k
            avg_pol = sum(s["policy"] for s in village_scores) / k
            avg_en = sum(s["effect"] for s in village_scores) / k
        else:
            village_avg_mech = None
            avg_pn = 30.0
            avg_pol = 15.0
            avg_en = 10.0

        # 机制运行得分计算方式：该乡镇机制运行得分与乡镇下属村的机制运行平均分
        if township_self_mech is not None and village_avg_mech is not None:
            avg_m = (township_self_mech + village_avg_mech) / 2.0
        elif township_self_mech is not None:
            avg_m = township_self_mech
        elif village_avg_mech is not None:
            avg_m = village_avg_mech
        else:
            avg_m = 15.0

        township_scores[t_name] = {
            "mech": avg_m,
            "prog_nei": avg_pn,
            "policy": avg_pol,
            "effect_nei": avg_en,
            "prog_wai": 20.0,
            "effect_wai": 10.0,
            "has_neiye": has_neiye,
            "has_waiye": False
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
            has_waiye = True
        else:
            avg_prog = 20.0
            avg_eff = 10.0
            has_waiye = False

        if t_name not in township_scores:
            township_scores[t_name] = {
                "mech": 15.0, "prog_nei": 30.0, "policy": 15.0, "effect_nei": 10.0,
                "prog_wai": avg_prog, "effect_wai": avg_eff,
                "has_neiye": False,
                "has_waiye": has_waiye
            }
        else:
            township_scores[t_name]["prog_wai"] = avg_prog
            township_scores[t_name]["effect_wai"] = avg_eff
            township_scores[t_name]["has_waiye"] = has_waiye
            
    for t_name, sc in township_scores.items():
        if sc.get("has_neiye") and sc.get("has_waiye"):
            m = sc["mech"]
            pn = sc["prog_nei"]
            pol = sc["policy"]
            en = sc["effect_nei"]
            pw = sc["prog_wai"]
            ew = sc["effect_wai"]
            sc["total"] = round(m + pn + pw + pol + en + ew, 1)
        else:
            sc["total"] = None
        
    return township_scores, county_mech, has_county

def calculate_county_averages(scores: dict, c_mech: float = 15.0, has_c: bool = False) -> dict:
    """
    计算全县各考核维度的加权平均分：
    - 仅以实际开展核查的乡镇数量作为各维度的平均分母，杜绝未评价乡镇稀释得分
    - 若某个维度没有任何乡镇开展核查，则默认满分基准
    """
    evaluated_neiye_mech = [s["mech"] for s in scores.values() if s and s.get("has_neiye")]
    if evaluated_neiye_mech:
        if has_c:
            county_mech = (sum(evaluated_neiye_mech) + c_mech) / (len(evaluated_neiye_mech) + 1)
        else:
            county_mech = sum(evaluated_neiye_mech) / len(evaluated_neiye_mech)
    else:
        county_mech = c_mech if has_c else 15.0

    evaluated_prog_nei = [s["prog_nei"] for s in scores.values() if s and s.get("has_neiye")]
    county_prog_nei = sum(evaluated_prog_nei) / len(evaluated_prog_nei) if evaluated_prog_nei else 30.0

    evaluated_policy = [s["policy"] for s in scores.values() if s and s.get("has_neiye")]
    county_policy = sum(evaluated_policy) / len(evaluated_policy) if evaluated_policy else 15.0

    evaluated_eff_nei = [s["effect_nei"] for s in scores.values() if s and s.get("has_neiye")]
    county_effect_nei = sum(evaluated_eff_nei) / len(evaluated_eff_nei) if evaluated_eff_nei else 10.0

    evaluated_prog_wai = [s["prog_wai"] for s in scores.values() if s and s.get("has_waiye")]
    county_prog_wai = sum(evaluated_prog_wai) / len(evaluated_prog_wai) if evaluated_prog_wai else 20.0

    evaluated_eff_wai = [s["effect_wai"] for s in scores.values() if s and s.get("has_waiye")]
    county_effect_wai = sum(evaluated_eff_wai) / len(evaluated_eff_wai) if evaluated_eff_wai else 10.0

    c_mech_r = round(county_mech, 1)
    c_pn_r = round(county_prog_nei, 1)
    c_pw_r = round(county_prog_wai, 1)
    c_pol_r = round(county_policy, 1)
    c_en_r = round(county_effect_nei, 1)
    c_ew_r = round(county_effect_wai, 1)

    return {
        "mech": c_mech_r,
        "prog_nei": c_pn_r,
        "prog_wai": c_pw_r,
        "policy": c_pol_r,
        "effect_nei": c_en_r,
        "effect_wai": c_ew_r,
        "prog_total": round(c_pn_r + c_pw_r, 1),
        "effect_total": round(c_en_r + c_ew_r, 1)
    }
