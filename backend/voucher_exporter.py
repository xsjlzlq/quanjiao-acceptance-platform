# -*- coding: utf-8 -*-
import os
import json
import uuid
import pythoncom
import win32com.client
import logging
from datetime import datetime
from collections import defaultdict

NUM_ZHS = ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十']

def num_to_zh(n):
    if 1 <= n <= 10:
        return NUM_ZHS[n-1]
    return str(n)

def export_voucher(qsdwdm, qsdwmc, form_data):
    base_dir = os.path.abspath(os.path.dirname(__file__))
    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        
        tpl_path = os.path.join(base_dir, "..", "附件", "核查凭证记录模板.doc")
        
        doc = word.Documents.Open(tpl_path)
        
        with open(os.path.join(base_dir, "hierarchy.json"), "r", encoding="utf-8") as f:
            hierarchy = json.load(f)
            
        evidences = form_data.get("evidences", {})
        
        content = ""
        
        # We need to construct the text and insert images
        if doc.Bookmarks.Exists("content"):
            rng = doc.Bookmarks("content").Range
            rng.Text = ""
            
            # Gather all checked options
            all_checked = []
            for k, v in form_data.items():
                if isinstance(v, list) and k != 'evidences':
                    all_checked.extend(v)
            
            tab_rng = rng.Duplicate
            tab_rng.Collapse(0)
            
            for t_idx, tab_dict in enumerate(hierarchy):
                tab_name = tab_dict["tab"]
                tab_has_content = False
                
                # Check if tab has any checked items
                for g in tab_dict["groups"]:
                    for opt in g["options"]:
                        if opt in all_checked:
                            tab_has_content = True
                            break
                    if tab_has_content: break
                
                if not tab_has_content:
                    continue
                    
                tab_rng.Text = f"{num_to_zh(t_idx + 1)}、{tab_name}\n"
                tab_rng.Font.Bold = True
                tab_rng.Collapse(0)
                
                for g_idx, g in enumerate(tab_dict["groups"]):
                    g_name = g["group"]
                    g_has_content = False
                    
                    for opt in g["options"]:
                        if opt in all_checked:
                            g_has_content = True
                            break
                            
                    if not g_has_content:
                        continue
                        
                    # Fix g_name, remove "1. " if present
                    if '.' in g_name:
                        g_name = g_name.split('.', 1)[1].strip()
                        
                    tab_rng.Text = f"{g_idx + 1}、{g_name}\n"
                    tab_rng.Font.Bold = False
                    tab_rng.Collapse(0)
                    
                    opt_count = 1
                    for opt in g["options"]:
                        if opt in all_checked:
                            tab_rng.Text = f"（{opt_count}）{opt}\n"
                            tab_rng.Collapse(0)
                            opt_count += 1
                            
                            if opt in evidences and len(evidences[opt]) > 0:
                                for img_info in evidences[opt]:
                                    img_url = img_info["url"]
                                    # Handle both URL formats: /uploads/xxx.jpg and /api/download?file=uploads/xxx.jpg
                                    if img_url.startswith("/uploads/"):
                                        abs_path = os.path.join(base_dir, "uploads", img_url[9:])
                                    elif "file=" in img_url:
                                        rel_path = img_url.split("file=")[1]
                                        abs_path = os.path.join(base_dir, "..", rel_path)
                                    else:
                                        abs_path = None
                                    
                                    if abs_path and os.path.exists(abs_path):
                                        # insert picture
                                        shape = tab_rng.InlineShapes.AddPicture(FileName=abs_path, LinkToFile=False, SaveWithDocument=True)
                                        
                                        # Scale if too large (A4 width is ~450 points, leaving margins)
                                        max_width = 400
                                        if shape.Width > max_width:
                                            ratio = max_width / shape.Width
                                            shape.Width = max_width
                                            shape.Height = shape.Height * ratio
                                        
                                        # Center the paragraph containing the shape
                                        tab_rng.SetRange(shape.Range.Start, shape.Range.End)
                                        tab_rng.ParagraphFormat.Alignment = 1 # Center
                                        
                                        # Move past the shape, insert newline, and reset alignment
                                        tab_rng.SetRange(shape.Range.End, shape.Range.End)
                                        tab_rng.Text = "\n"
                                        tab_rng.Collapse(0)
                                        tab_rng.ParagraphFormat.Alignment = 0 # Left

        
        jcz_name = form_data.get("jcz_name", "")
        fhz_name = form_data.get("fhz_name", "")
        
        if doc.Bookmarks.Exists("jcz"):
            doc.Bookmarks("jcz").Range.Text = jcz_name or ""
        if doc.Bookmarks.Exists("fhz"):
            doc.Bookmarks("fhz").Range.Text = fhz_name or ""

        if doc.Bookmarks.Exists("date"):
            rng = doc.Bookmarks("date").Range
            rng.Text = datetime.now().strftime("%Y年%m月%d日")
            
        out_filename = f"核查凭证记录_{qsdwmc}.doc"
        out_path = os.path.join(base_dir, "downloads", out_filename)
        doc.SaveAs(out_path)
        doc.Close(SaveChanges=False)
        word.Quit()
        word = None
        
        return f"/api/download?file=downloads/{out_filename}"
        
    except Exception as e:
        import traceback
        with open(os.path.join(base_dir, "voucher_error.log"), "w", encoding="utf-8") as err_f:
            traceback.print_exc(file=err_f)
        logging.exception("Voucher export failed")
        if word:
            try:
                word.Quit()
            except:
                pass
        return None
    finally:
        pythoncom.CoUninitialize()
