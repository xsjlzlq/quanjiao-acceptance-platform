with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\frontend\src\views\NeiyeForm.vue", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update import
code = code.replace(
    "import { ref, computed, onMounted } from 'vue';",
    "import { ref, computed, onMounted, onUnmounted } from 'vue';"
)

# 2. Add lastAutoSaveTime and silentAutoSave
auto_save_script = """
const lastAutoSaveTime = ref('');
let autoSaveTimer = null;

const silentAutoSave = async () => {
  if (!selectedAreaCode.value) return;
  try {
    const res = await axios.post('/api/save_neiye', {
      qsdwdm: selectedAreaCode.value,
      qsdwmc: selectedAreaName.value,
      level: selectedAreaLevel.value,
      form_data: form.value,
      score: totalScore.value
    });
    if (res.data.code === 200) {
      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
      lastAutoSaveTime.value = timeStr;
      showToast({ message: `内业评分已自动保存 (${timeStr})`, position: 'bottom', duration: 1500 });
    }
  } catch(e) {
    console.warn('内业自动保存异常', e);
  }
};
"""

# Insert auto_save_script before onMounted
pos_on_mounted = code.find("onMounted(async () => {")
if pos_on_mounted != -1:
    code = code[:pos_on_mounted] + auto_save_script + "\n" + code[pos_on_mounted:]

# Add timer in onMounted and onUnmounted hook
code = code.replace(
    "  } finally {\n    closeToast();\n  }\n});",
    "  } finally {\n    closeToast();\n  }\n  autoSaveTimer = setInterval(silentAutoSave, 5 * 60 * 1000);\n});\n\nonUnmounted(() => {\n  if (autoSaveTimer) clearInterval(autoSaveTimer);\n  silentAutoSave();\n});"
)

# Update score-display UI in template
old_score_disp = """      <div class="score-display">
        <div class="score-label">{{ selectedAreaName }} 内业得分：</div>
        <div class="score-val">{{ totalScore }} <span class="score-max">/ {{ selectedAreaLevel === 'county' ? 15 : 70 }}分</span></div>
      </div>"""

new_score_disp = """      <div class="score-display">
        <div>
          <div class="score-label">{{ selectedAreaName }} 内业得分：</div>
          <div style="font-size: 11px; font-weight: normal; color: #999; margin-top: 2px;">
            <van-icon name="passed" color="#07c160" /> 5分钟自动保存已启用 <span v-if="lastAutoSaveTime">(上次保存: {{ lastAutoSaveTime }})</span>
          </div>
        </div>
        <div class="score-val">{{ totalScore }} <span class="score-max">/ {{ selectedAreaLevel === 'county' ? 15 : 70 }}分</span></div>
      </div>"""

code = code.replace(old_score_disp, new_score_disp)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\frontend\src\views\NeiyeForm.vue", "w", encoding="utf-8") as f:
    f.write(code)

print("NeiyeForm.vue auto-save updated successfully.")