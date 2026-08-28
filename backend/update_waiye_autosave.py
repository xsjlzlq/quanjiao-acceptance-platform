with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\frontend\src\views\WaiyeForm.vue", "r", encoding="utf-8") as f:
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
  if (!currentGroupCode.value || groupSamples.value.length === 0) return;
  try {
    const payload = {
      records: groupSamples.value.map(item => ({
        id: item.id,
        area_acknowledged: item.area_acknowledged,
        rights_correct: item.rights_correct,
        bound_correct: item.bound_correct,
        member_qualified: item.member_qualified,
        self_verified: item.self_verified,
        self_signed: item.self_signed,
        satisfaction: item.satisfaction,
        survey_method: item.survey_method
      }))
    };
    const res = await axios.post('/api/waiye/save_records', payload);
    if (res.data.code === 200) {
      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
      lastAutoSaveTime.value = timeStr;
      showToast({ message: `外业核查已自动保存 (${timeStr})`, position: 'bottom', duration: 1500 });
      await fetchTownshipsSummary();
    }
  } catch(e) {
    console.warn('外业自动保存异常', e);
  }
};
"""

# Insert auto_save_script before onMounted
pos_on_mounted = code.find("onMounted(async () => {")
if pos_on_mounted != -1:
    code = code[:pos_on_mounted] + auto_save_script + "\n" + code[pos_on_mounted:]

# Add timer in onMounted and onUnmounted hook
code = code.replace(
    "  initExportPickerColumns();\n});",
    "  initExportPickerColumns();\n  autoSaveTimer = setInterval(silentAutoSave, 5 * 60 * 1000);\n});\n\nonUnmounted(() => {\n  if (autoSaveTimer) clearInterval(autoSaveTimer);\n  silentAutoSave();\n});"
)

# Update group-title UI in template
old_group_title = """            <div class="group-title">
              <span>{{ currentTownshipName }} / {{ currentVillageName }} / {{ currentGroupName }}</span>
              <van-tag type="primary" size="medium">{{ groupSamples.length }} 块地</van-tag>
            </div>"""

new_group_title = """            <div class="group-title">
              <div>
                <div>{{ currentTownshipName }} / {{ currentVillageName }} / {{ currentGroupName }}</div>
                <div style="font-size: 11px; font-weight: normal; color: #999; margin-top: 2px;">
                  <van-icon name="passed" color="#07c160" /> 5分钟自动保存已启用 <span v-if="lastAutoSaveTime">(上次保存: {{ lastAutoSaveTime }})</span>
                </div>
              </div>
              <van-tag type="primary" size="medium">{{ groupSamples.length }} 块地</van-tag>
            </div>"""

code = code.replace(old_group_title, new_group_title)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\frontend\src\views\WaiyeForm.vue", "w", encoding="utf-8") as f:
    f.write(code)

print("WaiyeForm.vue auto-save updated successfully.")