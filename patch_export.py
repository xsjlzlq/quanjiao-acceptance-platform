import re

with open('frontend/src/views/WaiyeForm.vue', 'r', encoding='utf-8') as f:
    text = f.read()

new_func = '''const initExportPickerColumns = async () => {
  try {
    const res = await axios.get('/api/villages');
    if (res.data.code === 200 && res.data.data) {
      const allData = res.data.data;
      let countyItem = null;
      let tsList = [];
      
      allData.forEach(item => {
        const codeStr = String(item.code);
        if (codeStr.endsWith('00000000') && codeStr.length === 14) {
          let name = item.name.replace(/安徽省|合肥市|芜湖市|蚌埠市|淮南市|马鞍山市|淮北市|铜陵市|安庆市|黄山市|阜阳市|宿州市|滁州市|六安市|宣城市|池州市|亳州市/g, '').trim();
          countyItem = {
            text: \\ (县级 - 导出附件9_外业组检查得分表)\,
            value: codeStr.substring(0, 6),
            level: 'county'
          };
        } else if (codeStr.endsWith('00000') && codeStr.length === 14) {
          tsList.push({
            text: \\ (乡镇级 - 导出附件8_外业组检查记录表)\,
            value: item.name,
            level: 'township',
            townshipName: item.name
          });
        }
      });
      
      exportPickerColumns.value = [];
      if (countyItem) exportPickerColumns.value.push(countyItem);
      exportPickerColumns.value.push(...tsList);
    }
  } catch (e) {
    console.error("Failed to load export picker columns", e);
  }
};'''

text = re.sub(r'const initExportPickerColumns = \(\) => \{[\s\S]*?\};', new_func, text)
text = text.replace('  initExportPickerColumns();', '  await initExportPickerColumns();')

with open('frontend/src/views/WaiyeForm.vue', 'w', encoding='utf-8') as f:
    f.write(text)

print('Updated export picker columns logic')