with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\frontend\src\views\WaiyeForm.vue", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update indicator in template
old_indicator = """                <div style="font-size: 11px; font-weight: normal; color: #999; margin-top: 2px;">
                  <van-icon name="passed" color="#07c160" /> 5分钟自动保存已启用 <span v-if="lastAutoSaveTime">(上次保存: {{ lastAutoSaveTime }})</span>
                </div>"""

new_indicator = """                <div v-if="autoSaveConfig.enabled" style="font-size: 11px; font-weight: normal; color: #999; margin-top: 2px;">
                  <van-icon name="passed" color="#07c160" /> {{ autoSaveConfig.interval }}分钟自动保存已启用 <span v-if="lastAutoSaveTime">(上次保存: {{ lastAutoSaveTime }})</span>
                </div>
                <div v-else style="font-size: 11px; font-weight: normal; color: #999; margin-top: 2px;">
                  <van-icon name="info-o" color="#faad14" /> 自动保存已关闭 <span style="color:#1989fa; cursor:pointer;" @click="$router.push('/settings')">(系统设置)</span>
                </div>"""

code = code.replace(old_indicator, new_indicator)

# 2. Update auto-save logic in script
old_vars = """const lastAutoSaveTime = ref('');
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
};"""

new_vars = """const AUTO_SAVE_KEY = 'auto_save_settings';
const autoSaveConfig = ref({ enabled: true, interval: 5 });
const lastAutoSaveTime = ref('');
let autoSaveTimer = null;

const loadAutoSaveConfig = () => {
  try {
    const raw = localStorage.getItem(AUTO_SAVE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      autoSaveConfig.value = {
        enabled: parsed.enabled !== false,
        interval: Number(parsed.interval) > 0 ? Math.max(1, Math.round(Number(parsed.interval))) : 5
      };
    } else {
      autoSaveConfig.value = { enabled: true, interval: 5 };
    }
  } catch (e) {
    autoSaveConfig.value = { enabled: true, interval: 5 };
  }
};

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
};"""

code = code.replace(old_vars, new_vars)

# 3. Update timer initialization in onMounted
old_timer_init = "  autoSaveTimer = setInterval(silentAutoSave, 5 * 60 * 1000);"
new_timer_init = """  loadAutoSaveConfig();
  if (autoSaveConfig.value.enabled) {
    const ms = autoSaveConfig.value.interval * 60 * 1000;
    autoSaveTimer = setInterval(silentAutoSave, ms);
  }"""

code = code.replace(old_timer_init, new_timer_init)

# 4. Update onUnmounted
old_unmount = """onUnmounted(() => {
  if (autoSaveTimer) clearInterval(autoSaveTimer);
  silentAutoSave();
});"""

new_unmount = """onUnmounted(() => {
  if (autoSaveTimer) {
    clearInterval(autoSaveTimer);
    autoSaveTimer = null;
  }
  if (autoSaveConfig.value.enabled) {
    silentAutoSave();
  }
});"""

code = code.replace(old_unmount, new_unmount)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\frontend\src\views\WaiyeForm.vue", "w", encoding="utf-8") as f:
    f.write(code)

print("WaiyeForm.vue patched successfully.")