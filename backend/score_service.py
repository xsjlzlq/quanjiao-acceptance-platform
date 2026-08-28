from sqlalchemy import text
from collections import defaultdict
from doc_exporter import calculate_neiye_subscores

async def get_all_township_scores(session):
    # Get Neiye
    res_nei = await session.execute(text("SELECT qsdwdm, qsdwmc, form_data FROM neiye_records"))
    nei_rows = res_nei.fetchall()
    
    township_scores = {}
    county_mech = 15.0
    has_county = False
    
    for r in nei_rows:
        fd = r[2] or {}
        scores = calculate_neiye_subscores(fd)["score"]
        if r[0] == '341124':
            county_mech = scores["mech"]
            has_county = True
        else:
            valid_names = ["襄河镇", "古河镇", "大墅镇", "二郎口镇", "武岗镇", "马厂镇", "石沛镇", "十字镇", "西王镇", "六镇镇"]
            if r[1] in valid_names:
                township_scores[r[1]] = {
                    "mech": scores["mech"],
                    "prog_nei": scores["prog"],
                    "policy": scores["policy"],
                    "effect_nei": scores["effect"],
                    "prog_wai": 20.0,
                    "effect_wai": 10.0
                }
        
    # Get Waiye
    res_wai = await session.execute(text("""
        SELECT township_name, group_code, 
               SUM(CASE WHEN area_acknowledged='X' THEN 1 ELSE 0 END +
                   CASE WHEN rights_correct='X' THEN 1 ELSE 0 END +
                   CASE WHEN bound_correct='X' THEN 1 ELSE 0 END +
                   CASE WHEN member_qualified='X' THEN 1 ELSE 0 END +
                   CASE WHEN self_verified='X' THEN 1 ELSE 0 END +
                   CASE WHEN self_signed='X' THEN 1 ELSE 0 END) as errors,
               SUM(CASE WHEN satisfaction='满意' THEN 1 ELSE 0 END) as sats,
               COUNT(*) as total
        FROM waiye_samples
        GROUP BY township_name, group_code
    """))
    wai_rows = res_wai.fetchall()
    
    wai_by_township = defaultdict(list)
    for r in wai_rows:
        t_name, g_code, errors, sats, total = r
        if total > 0:
            prog = max(20.0 - float(errors) * 0.5, 0.0)
            eff = (float(sats) / total * 10.0)
            wai_by_township[t_name].append((prog, eff))
            
    for t_name, sc in wai_by_township.items():
        avg_prog = sum(x[0] for x in sc) / len(sc)
        avg_eff = sum(x[1] for x in sc) / len(sc)
        if t_name not in township_scores:
            township_scores[t_name] = {
                "mech": 15.0, "prog_nei": 30.0, "policy": 15.0, "effect_nei": 10.0,
                "prog_wai": avg_prog, "effect_wai": avg_eff
            }
        else:
            township_scores[t_name]["prog_wai"] = avg_prog
            township_scores[t_name]["effect_wai"] = avg_eff
            
    for t_name, sc in township_scores.items():
        sc["total"] = sc["mech"] + sc["prog_nei"] + sc["policy"] + sc["effect_nei"] + sc["prog_wai"] + sc["effect_wai"]
        
    return township_scores, county_mech, has_county
