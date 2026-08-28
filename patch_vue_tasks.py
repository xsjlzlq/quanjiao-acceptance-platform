import sys
import re

with open('frontend/src/views/Tasks.vue', 'r', encoding='utf-8') as f:
    code = f.read()

# Add radio button for mode 3
code = code.replace('<van-radio :name="2">按乡镇自动抽组及5%农户</van-radio>', 
'<van-radio :name="2">按乡镇自动抽组及5%农户</van-radio>\n                <van-radio :name="3">按导入表格抽样</van-radio>')

# Add Mode 3 template
mode3_template = """        <!-- Mode 3: Excel Upload -->
        <van-cell-group inset title="上传抽样表格 (方式三)" v-if="mode === 3" style="margin-top: 16px;">
          <van-cell title="上传文件">
            <template #label>
              <van-uploader v-model="fileList" accept=".xls,.xlsx" max-count="1" />
            </template>
          </van-cell>
          <div style="padding:0 16px; font-size:12px; color:#999; margin-bottom:10px;">
            表格需包含表头：发包方编码，乡镇名，村名，组名，抽样农户数。<br/>
            如填写了抽样农户数按实际抽取，留空则默认按 5% 向上取整抽取。
          </div>
        </van-cell-group>"""

code = code.replace('<!-- Mode 2: Auto selection -->', mode3_template + '\n\n        <!-- Mode 2: Auto selection -->')

# In script setup, add fileList
code = code.replace("const manualCount = ref('');", "const manualCount = ref('');\nconst fileList = ref([]);")

# Add mode 3 logic in generateSamples
mode3_logic = """  if (mode.value === 3) {
    if (fileList.value.length === 0) {
      showToast('请先上传表格文件');
      return;
    }
    const formData = new FormData();
    formData.append('file', fileList.value[0].file);
    
    loading.value = true;
    try {
      const res = await axios.post('/api/sample_by_excel', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      if (res.data.code === 200) {
        showToast({ type: 'success', message: '抽样成功！文件已生成。' });
        files.value = res.data.urls.map(u => ({
          name: u.split('file=downloads/')[1],
          url: u
        }));
      } else { showToast(res.data.message || '抽样异常'); }
    } catch(e) {
      showToast('请求失败');
    } finally { loading.value = false; }
    return;
  }"""

code = code.replace("loading.value = true;\n  try {", mode3_logic + "\n\n  loading.value = true;\n  try {")

with open('frontend/src/views/Tasks.vue', 'w', encoding='utf-8') as f:
    f.write(code)

print("Tasks.vue patched.")
