import os
import shutil
import pythoncom
import win32com.client

def test_export():
    pythoncom.CoInitialize()
    try:
        word = win32com.client.DispatchEx('Word.Application')
        word.Visible = False
        word.DisplayAlerts = False
        
        os.makedirs('downloads', exist_ok=True)
        
        # --- Process 附件5 ---
        att5_template = os.path.abspath(r'附件\附件5.doc')
        att5_out = os.path.abspath(r'downloads\附件5_test.doc')
        shutil.copy(att5_template, att5_out)
        
        doc5 = word.Documents.Open(att5_out)
        t5 = doc5.Tables(1)
        t5.Cell(2, 1).Range.Text = "1"
        t5.Cell(2, 2).Range.Text = "测试镇"
        doc5.Save()
        doc5.Close(False)
        print("Att5 saved")
        
        # --- Process 附件8 ---
        att8_template = os.path.abspath(r'附件\附件8.doc')
        att8_out = os.path.abspath(r'downloads\附件8_test.doc')
        shutil.copy(att8_template, att8_out)
        
        doc8 = word.Documents.Open(att8_out)
        t8 = doc8.Tables(1)
        for _ in range(5):
            t8.Rows(3).Delete()
            
        t8.Rows.Add(t8.Rows(3))
        t8.Cell(2, 1).Range.Text = "1"
        t8.Cell(2, 2).Range.Text = "张三"
        doc8.Save()
        doc8.Close(False)
        print("Att8 saved")
        
        word.Quit()
    except Exception as e:
        print("Error:", e)
    finally:
        pythoncom.CoUninitialize()

test_export()
