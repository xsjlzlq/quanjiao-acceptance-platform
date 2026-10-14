# -*- coding: utf-8 -*-
import os
import json
import uuid
import pythoncom
import win32com.client
import logging
from datetime import datetime
from PIL import Image, ImageOps
from database import get_base_dir

NUM_ZHS = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']

def num_to_zh(n):
    if 1 <= n <= 10:
        return NUM_ZHS[n-1]
    return str(n)

# 内置最新的内业核查标准层级（解耦不存在的外部 hierarchy.json）
NEIYE_HIERARCHY = [
    {
        "tab": "机制运行",
        "groups": [
            {
                "field": "mech_1",
                "group": "延包方案与分工",
                "options": ["未制定方案", "方案未盖章或非红头", "直接套用上级方案", "分工不明确", "制定程序不合法", "方案缺少"]
            },
            {
                "field": "mech_2",
                "group": "经费保障",
                "options": ["支付不规范", "支付不及时", "经费没有县级兜底"]
            },
            {
                "field": "mech_3",
                "group": "宣传",
                "options": ["没有宣传材料", "宣传材料无效", "宣传途径单一"]
            },
            {
                "field": "mech_4",
                "group": "培训",
                "options": ["没有培训材料", "没有分批次培训", "培训材料不齐全", "培训未覆盖县乡村组", "培训材料无效"]
            }
        ]
    },
    {
        "tab": "程序规范",
        "groups": [
            {
                "field": "prog_1",
                "group": "成立机构",
                "options": ["未召开村民会议", "未选举产生理事会", "未公示理事会名单", "公示时间不足3天", "参会人数不足法定数量", "违规召开村民会议", "理事会成员非本集体经济组织"]
            },
            {
                "field": "prog_2",
                "group": "摸底核实",
                "options": [
                    "没有进行摸底", "摸底表农户未签署", "摸底表中没有表达延包意愿", "摸底表其它签署不齐全",
                    "特殊人员摸底不清或未统计", "户变化未统计", "矛盾纠纷未登记", "矛盾纠纷未登记不完整",
                    "本级矛盾纠纷没有处理记录", "承包地变化未摸清", "没有应确尽确", "没有统计新增耕地、机耕地",
                    "没有统计补充确权", "没有统计新增确权确亩不确界或未说明", "没有统计小调整或未说明",
                    "各类统计资料没有封面", "各类统计资料没有签章", "各类统计资料统计不正确", "摸底与其它材料时间矛盾"
                ]
            },
            {
                "field": "prog_3",
                "group": "制定方案",
                "options": [
                    "没有延包方案草案", "没有延包方案", "延包方案未上报", "延包方案未公示",
                    "未召开会议讨论延包方案", "延包方案上报与通过会议时间顺序不正确",
                    "延包方案与工作方案混淆", "理事会与工作领导小组混淆"
                ]
            },
            {
                "field": "prog_4",
                "group": "调查公示",
                "options": [
                    "没有公示材料", "没有公示或公示不足15天", "公示不足15天", "公示结果未确认（归户表没签署）", "公示结果未确认",
                    "各类资料不齐全", "各类资料制作粗糙", "各类资料签署不规范",
                    "权属证明材料不齐全", "其它证明材料不齐全", "各类资料间时间顺序混乱"
                ]
            },
            {
                "field": "prog_5",
                "group": "签订合同",
                "options": ["合同版本格式不正确", "合同网签率未达到95%", "没有地块示意图"]
            },
            {
                "field": "prog_6",
                "group": "完善证书",
                "options": [
                    "未进行信息共享", "未与不动产登记部门有序衔接", "承包地块间重叠",
                    "承包地块与宅基地重叠", "承包地块与其它自然资源部门要求的要素重叠",
                    "缺少登记要件", "资料格式不符合登记要求"
                ]
            },
            {
                "field": "prog_7",
                "group": "资料归档",
                "options": [
                    "档案整理第三方无涉密档案整理资质", "没有进行档案验收", "档案验收不符合相关标准",
                    "档案资料涂改多处", "档案资料缺少主体内容", "档案资料缺少佐证内容",
                    "档案资料背考表签署不正确", "档案资料存在大量漏签署", "档案资料姓名错误未检查",
                    "档案资料收集不齐全", "档案分类不符合要求", "档号与归档章不一致", "档案变数字化瑕疵", "“一户一档”姓名著录错误"
                ]
            }
        ]
    },
    {
        "tab": "政策落实",
        "groups": [
            {
                "field": "policy_1",
                "group": "“大稳定、小调整”落实情况",
                "options": ["小调整比率过大或手续不齐全", "打乱重分", "违法调整或收回承包地", "没有小调整统计资料或说明"]
            },
            {
                "field": "policy_2",
                "group": "保障土地承包权益",
                "options": ["未保障特殊群体权益", "未保障无地户权益", "没有统计（关注）特殊群体"]
            },
            {
                "field": "policy_3",
                "group": "依法收回消亡户承包地",
                "options": ["没有应收尽收", "采用不正当方式隐匿消亡户", "违规处置消亡土地", "没有统计消亡户", "没有分清实际消亡户和伪消亡户"]
            },
            {
                "field": "policy_4",
                "group": "严格机动地和新增耕地管理",
                "options": ["机动地、新增耕地处置不当", "机动地比率过高", "未统计机动地和新增耕地"]
            },
            {
                "field": "policy_5",
                "group": "从严掌握确权确股不确地",
                "options": ["违背农户意愿强行推进", "确权确股不确地手续不齐全", "没有统计新增确权确亩不确界"]
            }
        ]
    },
    {
        "tab": "工作成效",
        "groups": [
            {
                "field": "effect_1",
                "group": "加强风险防范",
                "options": ["未建立矛盾纠纷处置机制", "未建立舆情处置办法", "没有矛盾纠纷处理台账", "矛盾纠纷处理台账填写不规范", "没有本级处理的矛盾纠纷处理记录"]
            }
        ]
    }
]

def resolve_photo_path(base_dir, raw_url):
    """自适应解析佐证照片的物理路径"""
    if not raw_url or not isinstance(raw_url, str):
        return None
    clean = raw_url.strip()
    if clean.startswith("/uploads/"):
        rel = clean.lstrip("/")
    elif "file=" in clean:
        rel = clean.split("file=")[-1].lstrip("/\\")
    else:
        rel = os.path.join("uploads", os.path.basename(clean))
        
    candidates = [
        os.path.join(base_dir, "backend", rel),
        os.path.join(base_dir, rel),
        os.path.join(base_dir, "backend", "uploads", os.path.basename(clean)),
        os.path.join(base_dir, "uploads", os.path.basename(clean)),
        os.path.abspath(clean)
    ]
    for c in candidates:
        if os.path.exists(c) and os.path.isfile(c):
            return os.path.abspath(c)
    return None

def export_voucher(qsdwdm, qsdwmc, form_data):
    """
    导出核查凭证记录 Word 文档 (.doc)
    基于附件/核查凭证记录模板.doc
    """
    base_dir = get_base_dir()
    pythoncom.CoInitialize()
    word = None
    doc = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        
        tpl_path = os.path.join(base_dir, "附件", "核查凭证记录模板.doc")
        clean_name = str(qsdwmc or qsdwdm or "内业").replace(" ", "").replace("/", "_")
        out_filename = f"核查凭证记录_{clean_name}.doc"
        out_path = os.path.join(base_dir, "backend", "downloads", out_filename)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        
        doc = word.Documents.Open(FileName=tpl_path, ReadOnly=False, ConfirmConversions=False)
        
        # 1. 替换大标题，加上核查对象名称
        p1 = doc.Paragraphs(1)
        p1.Range.Text = f"【{qsdwmc}】内业核查凭证记录\r"
        p1.Range.Font.Name = "黑体"
        p1.Range.Font.Size = 16
        p1.Range.Font.Bold = True
        p1.Range.ParagraphFormat.Alignment = 1
        
        evidences = form_data.get("evidences", {}) or {}
        
        # 收集所有已勾选或有数量的问题项
        all_checked = set()
        for k, v in form_data.items():
            if isinstance(v, list) and k != "evidences":
                for itm in v:
                    if itm: all_checked.add(str(itm).strip())
            elif k.startswith("policy_2_") or k.startswith("policy_3_"):
                if k.endswith("_other") or k.endswith("_desc") or k.endswith("_checked"):
                    continue
                try:
                    cnt_val = int(v or 0)
                except (ValueError, TypeError):
                    cnt_val = 0
                if cnt_val > 0:
                    # 步进器项标签映射
                    label_map = {
                        "policy_2_1": "未保障特殊群体权益",
                        "policy_2_2": "未保障无地户权益",
                        "policy_2_3": "没有统计（关注）特殊群体",
                        "policy_3_1": "没有应收尽收",
                        "policy_3_2": "采用不正当方式隐匿消亡户",
                        "policy_3_3": "违规处置消亡土地",
                        "policy_3_4": "没有统计消亡户",
                        "policy_3_5": "没有分清实际消亡户和伪消亡户",
                    }
                    if k in label_map:
                        all_checked.add(label_map[k])
                        
        # 2. 填充 content 书签
        if doc.Bookmarks.Exists("content"):
            rng = doc.Bookmarks("content").Range
            rng.Text = ""
            
            tab_rng = rng.Duplicate
            tab_rng.Collapse(0)
            
            has_any_content = False
            
            for t_idx, tab_dict in enumerate(NEIYE_HIERARCHY):
                tab_name = tab_dict["tab"]
                
                # 判断该 Tab 是否有选中的问题（包括预设项和“其他”项）
                tab_groups_with_issues = []
                for g in tab_dict["groups"]:
                    fld = g.get("field")
                    g_opts = []
                    # 预设项
                    for o in g["options"]:
                        if o in all_checked:
                            g_opts.append((o, o, [o]))
                    # “其他”项
                    has_other = False
                    if fld:
                        if isinstance(form_data.get(fld), list) and "其他" in form_data.get(fld, []):
                            has_other = True
                        elif form_data.get(f"{fld}_other_checked"):
                            has_other = True
                    if has_other:
                        other_txt = str(form_data.get(f"{fld}_other") or form_data.get(f"{fld}_other_desc") or "").strip()
                        label_show = f"其他：{other_txt}" if other_txt else "其他"
                        # 查找佐证照片的可能 key
                        ev_keys = [f"{fld}_其他", "其他"]
                        g_opts.append(("其他", label_show, ev_keys))

                    if g_opts:
                        tab_groups_with_issues.append((g["group"], g_opts))
                        
                if not tab_groups_with_issues:
                    continue
                    
                has_any_content = True
                
                # 插入大类标题（如：一、机制运行）
                tab_rng.Text = f"{num_to_zh(t_idx + 1)}、{tab_name}\r"
                tab_rng.Font.Name = "黑体"
                tab_rng.Font.Size = 13
                tab_rng.Font.Bold = True
                tab_rng.ParagraphFormat.Alignment = 0
                tab_rng.ParagraphFormat.SpaceBefore = 8
                tab_rng.ParagraphFormat.SpaceAfter = 4
                tab_rng.Collapse(0)
                
                for g_idx, (g_name, g_opts) in enumerate(tab_groups_with_issues, 1):
                    # 插入子项标题（如：1、配套延包政策文件）
                    tab_rng.Text = f"{g_idx}、{g_name}\r"
                    tab_rng.Font.Name = "黑体"
                    tab_rng.Font.Size = 11.5
                    tab_rng.Font.Bold = True
                    tab_rng.ParagraphFormat.Alignment = 0
                    tab_rng.ParagraphFormat.SpaceBefore = 4
                    tab_rng.ParagraphFormat.SpaceAfter = 2
                    tab_rng.Collapse(0)
                    
                    for o_idx, (raw_opt, display_name, ev_search_keys) in enumerate(g_opts, 1):
                        # 插入问题描述（如：（1）未制定方案 或 （2）其他：具体说明）
                        tab_rng.Text = f"（{o_idx}）{display_name}\r"
                        tab_rng.Font.Name = "仿宋"
                        tab_rng.Font.Size = 11
                        tab_rng.Font.Bold = False
                        tab_rng.ParagraphFormat.Alignment = 0
                        tab_rng.ParagraphFormat.SpaceBefore = 2
                        tab_rng.ParagraphFormat.SpaceAfter = 4
                        tab_rng.Collapse(0)
                        
                        # 检查并插入该项问题上传的佐证照片
                        p_objs = []
                        for ek in ev_search_keys:
                            if ek in evidences and evidences[ek]:
                                p_objs.extend(evidences[ek])

                        inserted_photos = 0
                        for p_obj in p_objs:
                            raw_u = p_obj.get("url") if isinstance(p_obj, dict) else str(p_obj)
                            abs_p = resolve_photo_path(base_dir, raw_u)
                            if abs_p:
                                try:
                                    shape = tab_rng.InlineShapes.AddPicture(FileName=abs_p, LinkToFile=False, SaveWithDocument=True)
                                    # 标准 A4 页面内缩放（最大宽度 380 磅，约 13.4 厘米）
                                    max_width = 380
                                    if shape.Width > max_width:
                                        ratio = max_width / shape.Width
                                        shape.Width = max_width
                                        shape.Height = shape.Height * ratio
                                        
                                    tab_rng.SetRange(shape.Range.Start, shape.Range.End)
                                    tab_rng.ParagraphFormat.Alignment = 1 # 居中
                                    tab_rng.SetRange(shape.Range.End, shape.Range.End)
                                    tab_rng.Text = "\r"
                                    tab_rng.Collapse(0)
                                    tab_rng.ParagraphFormat.Alignment = 0
                                    inserted_photos += 1
                                except Exception as pe:
                                    print(f"Insert evidence picture error: {pe}")
                                    
                        if inserted_photos == 0:
                            tab_rng.Text = "（暂无上传照片佐证）\r"
                            tab_rng.Font.Name = "仿宋"
                            tab_rng.Font.Size = 10
                            tab_rng.Font.Color = 8421504 # 灰色
                            tab_rng.ParagraphFormat.Alignment = 0
                            tab_rng.ParagraphFormat.SpaceBefore = 0
                            tab_rng.ParagraphFormat.SpaceAfter = 6
                            tab_rng.Collapse(0)

            if not has_any_content:
                tab_rng.Text = f"经内业核查，核查对象【{qsdwmc}】未勾选发现扣分问题项。\r"
                tab_rng.Font.Name = "仿宋"
                tab_rng.Font.Size = 12
                tab_rng.Font.Color = 8421504
                tab_rng.ParagraphFormat.Alignment = 1
                tab_rng.ParagraphFormat.SpaceBefore = 30
                tab_rng.Collapse(0)

        # 3. 填充人员与日期书签
        jcz_name = form_data.get("jcz_name", "") or ""
        fhz_name = form_data.get("fhz_name", "") or ""
        
        if doc.Bookmarks.Exists("jcz"):
            try:
                doc.Bookmarks("jcz").Range.Text = f" {jcz_name} " if jcz_name else "       "
            except Exception: pass
            
        if doc.Bookmarks.Exists("fhz"):
            try:
                doc.Bookmarks("fhz").Range.Text = f" {fhz_name} " if fhz_name else "       "
            except Exception: pass

        if doc.Bookmarks.Exists("date"):
            try:
                rng_d = doc.Bookmarks("date").Range
                rng_d.Text = datetime.now().strftime("%Y年%m月%d日")
            except Exception: pass
            
        doc.SaveAs2(FileName=out_path, FileFormat=0)
        doc.Close(0)
        doc = None
        word.Quit()
        word = None
        
        return f"/api/download?file=downloads/{out_filename}"
    except Exception as e:
        import traceback
        traceback.print_exc()
        if doc:
            try: doc.Close(0)
            except: pass
        if word:
            try: word.Quit()
            except: pass
        return None
    finally:
        pythoncom.CoUninitialize()
