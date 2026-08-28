import os
import win32com.client

doc_path = os.path.abspath(r'plan\全椒县县级自验工作方案0818_latest.docx')
out_dir = os.path.abspath('附件')
if not os.path.exists(out_dir):
    os.makedirs(out_dir)

word = win32com.client.DispatchEx('Word.Application')
word.Visible = False

try:
    print('Opening document...')
    doc = word.Documents.Open(doc_path, ReadOnly=True)
    print('Document opened.')
    
    ranges = []
    for i in range(1, 14):
        att_text = f'附件{i}'
        found = False
        for p in doc.Paragraphs:
            text = p.Range.Text.strip()
            if text.startswith(att_text) or text.startswith(f'附件 {i}'):
                if p.Range.Start > 1000:
                    ranges.append((att_text, p.Range.Start))
                    found = True
                    break
        if not found:
            print(f'Missing {att_text}')

    ranges.append(("EOF", doc.Content.End))
    doc.Close(False)
    
    print('Positions found:', ranges)
    
    # Extract each attachment by copy-pasting the exact range to avoid modifying the original layout
    # Wait, the prompt says "每个附件保存为doc格式，样式不能改变" (save as .doc, format must not change).
    # Deleting nodes from a cloned document is the best way to retain headers, footers, page orientation, etc.
    
    wdFormatDocument = 0
    for i in range(len(ranges)-1):
        att_name = ranges[i][0]
        start_pos = ranges[i][1]
        end_pos = ranges[i+1][1]
        
        print(f'Extracting {att_name} ...')
        doc = word.Documents.Open(doc_path, ReadOnly=True)
        
        if end_pos < doc.Content.End:
            doc.Range(end_pos, doc.Content.End).Delete()
            
        if start_pos > 0:
            doc.Range(0, start_pos).Delete()
            
        out_file = os.path.join(out_dir, f"{att_name}.doc")
        doc.SaveAs(out_file, FileFormat=wdFormatDocument)
        doc.Close(False)
        print(f'Saved {att_name}')

except Exception as e:
    print('Error:', e)

word.Quit()
print("All done.")
