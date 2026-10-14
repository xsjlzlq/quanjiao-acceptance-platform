from sqlalchemy import text
from collections import defaultdict
from doc_exporter import calculate_neiye_subscores
from database import parse_qsdwdmb_hierarchy

async def get_all_township_scores(session, exclude_severe: bool = False):
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
    county_effect = 10.0
    has_county = False
    
    # 将内业记录按代码建立索引
    records_dict = {}
    for r in nei_rows:
        q_dm, q_mc, fd, lvl = str(r[0]), r[1], r[2] or {}, r[3]
        scores = calculate_neiye_subscores(fd, exclude_severe=exclude_severe)["score"]
        records_dict[q_dm] = scores
        if q_dm == county_code or lvl == 'county':
            county_mech = scores["mech"]
            county_effect = scores["effect"]
            has_county = True

    # 按照各乡镇下抽样村与乡镇本级的得分计算平均分
    for t_item in township_list:
        t_name = t_item["name"]
        t_code = t_item["code"]
        v_codes = ts_v_map.get(t_name, [])
        
        # 获取该乡镇自身的机制运行与工作成效得分 (qsdwdm == t_code)
        township_self_mech = records_dict.get(t_code, {}).get("mech")
        township_self_effect = records_dict.get(t_code, {}).get("effect")

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

        has_neiye = bool(village_scores) or (township_self_mech is not None) or (township_self_effect is not None)
        if village_scores:
            k = len(village_scores)
            village_avg_mech = sum(s["mech"] for s in village_scores) / k
            avg_pn = sum(s["prog"] for s in village_scores) / k
            avg_pol = sum(s["policy"] for s in village_scores) / k
            village_avg_effect = sum(s["effect"] for s in village_scores) / k
        else:
            village_avg_mech = None
            avg_pn = 30.0
            avg_pol = 15.0
            village_avg_effect = None

        # 机制运行得分计算方式：该乡镇机制运行得分与乡镇下属村的机制运行平均分
        if township_self_mech is not None and village_avg_mech is not None:
            avg_m = (township_self_mech + village_avg_mech) / 2.0
        elif township_self_mech is not None:
            avg_m = township_self_mech
        elif village_avg_mech is not None:
            avg_m = village_avg_mech
        else:
            avg_m = 15.0

        # 工作成效得分计算方式：该乡镇工作成效得分与乡镇下属村的工作成效平均分
        if township_self_effect is not None and village_avg_effect is not None:
            avg_en = (township_self_effect + village_avg_effect) / 2.0
        elif township_self_effect is not None:
            avg_en = township_self_effect
        elif village_avg_effect is not None:
            avg_en = village_avg_effect
        else:
            avg_en = 10.0

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
        
    # Get Waiye (计算规则：村得分由各组得分平均值，乡镇得分为各村平均值，与附件9 export_waiye_att9 保持完全一致的去重与扣分标准)
    res_wai = await session.execute(text("""
        SELECT township_name, village_name, group_name,
               cbfbm, cbfbm_short, cbfmc,
               area_acknowledged, rights_correct, bound_correct, member_qualified,
               self_verified, self_signed, satisfaction, phone_correct
        FROM waiye_samples
        ORDER BY township_name, village_name, group_name, cbfbm, id
    """))
    wai_rows = res_wai.fetchall()
    
    groups_map = defaultdict(list)
    for r in wai_rows:
        t_n, v_n, g_n = r[0], r[1], r[2]
        if t_n:
            groups_map[(t_n, v_n, g_n)].append({
                "cbfbm": r[3], "cbfbm_short": r[4], "cbfmc": r[5],
                "area_acknowledged": r[6], "rights_correct": r[7], "bound_correct": r[8],
                "member_qualified": r[9], "self_verified": r[10], "self_signed": r[11],
                "satisfaction": r[12], "phone_correct": r[13]
            })

    wai_hierarchy = defaultdict(lambda: defaultdict(list))
    for (t_name, v_name, g_name), g_rows in groups_map.items():
        total_errors = 0
        satisfaction_count = 0
        processed_cbfs = set()
        c_cnt = 0
        for r in g_rows:
            # 地块错误项：面积不认可属于严重问题；四至不正确、非本人核实属于非严重问题
            dk_keys = ["bound_correct", "self_verified"] if exclude_severe else ["area_acknowledged", "bound_correct", "self_verified"]
            for k in dk_keys:
                if r.get(k) == "X":
                    total_errors += 1
            
            cbf_key = str(r.get("cbfbm") or r.get("cbfbm_short") or r.get("cbfmc") or "")
            if cbf_key not in processed_cbfs:
                processed_cbfs.add(cbf_key)
                c_cnt += 1
                # 农户错误项：权属不正确、成员不符合、非本人签名属于严重问题；联系电话不正确属于非严重问题
                if not exclude_severe:
                    for k in ["rights_correct", "member_qualified", "self_signed"]:
                        if r.get(k) == "X":
                            total_errors += 1
                if str(r.get("phone_correct", "")).strip() == "X":
                    total_errors += 1
                if r.get("satisfaction") == "满意":
                    satisfaction_count += 1
                
        c_cnt = c_cnt if c_cnt > 0 else len(g_rows)
        prog_score = max(20.0 - total_errors * 0.5, 0.0)
        effect_score = (satisfaction_count / c_cnt * 10.0) if c_cnt > 0 else 10.0
        wai_hierarchy[t_name][v_name].append((prog_score, effect_score))
            
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
        
    return township_scores, county_mech, has_county, county_effect

def calculate_county_averages(scores: dict, c_mech: float = 15.0, has_c: bool = False, c_eff: float = 10.0) -> dict:
    """
    计算全县各考核维度的加权平均分：
    - 机制运行与工作成效：包含县本级自查得分与各乡镇得分加权平均
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
    if evaluated_eff_nei:
        if has_c:
            county_effect_nei = (sum(evaluated_eff_nei) + c_eff) / (len(evaluated_eff_nei) + 1)
        else:
            county_effect_nei = sum(evaluated_eff_nei) / len(evaluated_eff_nei)
    else:
        county_effect_nei = c_eff if has_c else 10.0

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
