import win32com.client, os, pythoncom, shutil
from PIL import Image, ImageDraw

# 1. Create a mock signature PNG
base_dir = r"G:\全椒县二轮延包\全椒县县级验收管理平台"
sig_dir = os.path.join(base_dir, "backend", "uploads", "signatures")
os.makedirs(sig_dir, exist_ok=True)
sig_path = os.path.join(sig_dir, "test_sig_0123.png")

img = Image.new("RGBA", (300, 120), (255, 255, 255, 0))
draw = ImageDraw.Draw(img)
# Draw mock signature strokes
draw.line([(20, 60), (60, 30), (100, 80), (150, 40), (220, 70), (280, 50)], fill="black", width=5)
draw.text((80, 70), "张三 (签名)", fill="blue")
img.save(sig_path, "PNG")
print("Mock signature image created:", sig_path)

# 2. Test Word COM table merging & image insertion on Attachment 8
pythoncom.CoInitialize()
word = win32com.client.DispatchEx("Word.Application")
word.Visible = False
word.DisplayAlerts = 0

tpl = os.path.join(base_dir, "附件", "附件8.doc")
out_path = os.path.join(base_dir, "backend", "downloads", "test_sig_att8.doc")
if os.path.exists(out_path):
    try: os.remove(out_path)
    except: pass
shutil.copy(tpl, out_path)

doc8 = word.Documents.Open(FileName=out_path, ReadOnly=False, ConfirmConversions=False)
t8 = doc8.Tables(1)

# Delete 5 default sample rows
for _ in range(5):
    try: t8.Rows(3).Delete()
    except: pass

# Insert 3 rows for a contractor who has 3 parcels, and 1 row for another contractor
# Total 4 rows
for _ in range(3):
    t8.Rows(2).Select()
    word.Selection.InsertRowsBelow(1)

# Rows are: Row 2, Row 3, Row 4 (Contractor A: 张三), Row 5 (Contractor B: 李四)
# Fill text
# 张三 row 1
t8.Cell(2, 1).Range.Text = "1"
t8.Cell(2, 2).Range.Text = "张三"
t8.Cell(2, 5).Range.Text = "地块1"

# 张三 row 2
t8.Cell(3, 1).Range.Text = "2"
t8.Cell(3, 2).Range.Text = "张三"
t8.Cell(3, 5).Range.Text = "地块2"

# 张三 row 3
t8.Cell(4, 1).Range.Text = "3"
t8.Cell(4, 2).Range.Text = "张三"
t8.Cell(4, 5).Range.Text = "地块3"

# 李四 row 4
t8.Cell(5, 1).Range.Text = "4"
t8.Cell(5, 2).Range.Text = "李四"
t8.Cell(5, 5).Range.Text = "地块4"

# Now merge Contractor A's Column 16 from Row 2 to Row 4
print("Merging Column 16 from Row 2 to Row 4...")
cell_top = t8.Cell(2, 16)
cell_bot = t8.Cell(4, 16)
cell_top.Merge(cell_bot)
print("Merged successfully!")

# Insert signature picture into the merged cell (Cell at Row 2, Col 16)
print("Inserting picture into merged cell...")
cell_top.Range.Text = ""
pic = cell_top.Range.InlineShapes.AddPicture(FileName=os.path.abspath(sig_path), LinkToFile=False, SaveWithDocument=True)
pic.Width = 65  # approx 2.3 cm width
pic.Height = 26 # approx 0.9 cm height
cell_top.Range.ParagraphFormat.Alignment = 1 # Center
cell_top.VerticalAlignment = 1 # Center
print("Picture inserted successfully!")

# Insert into single cell Row 5 (李四)
cell_li = t8.Cell(5, 16)
cell_li.Range.Text = ""
pic2 = cell_li.Range.InlineShapes.AddPicture(FileName=os.path.abspath(sig_path), LinkToFile=False, SaveWithDocument=True)
pic2.Width = 65
pic2.Height = 26
cell_li.Range.ParagraphFormat.Alignment = 1
cell_li.VerticalAlignment = 1

doc8.SaveAs2(FileName=out_path, FileFormat=0)
doc8.Close(0)
word.Quit()
pythoncom.CoUninitialize()
print("All signature attachment 8 tests passed successfully!")