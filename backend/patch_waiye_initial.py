with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\frontend\src\views\WaiyeForm.vue", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update fetchWaiyeHierarchy to remove auto selection
old_fetch = """const fetchWaiyeHierarchy = async () => {
  try {
    const res = await axios.get('/api/waiye/hierarchy');
    if (res.data.code === 200) {
      cascaderOptions.value = res.data.tree || [];
      if (cascaderOptions.value.length > 0 && !currentGroupCode.value) {
        const firstTs = cascaderOptions.value[0];
        if (firstTs.children && firstTs.children.length > 0) {
          const firstVill = firstTs.children[0];
          if (firstVill.children && firstVill.children.length > 0) {
            const firstGroup = firstVill.children[0];
            selectGroup(firstTs.township_name, firstVill.village_name, firstGroup.group_name, firstGroup.group_code);
          }
        }
      }
    }
  } catch(e) {
    console.error(e);
  }
};"""

new_fetch = """const fetchWaiyeHierarchy = async () => {
  try {
    const res = await axios.get('/api/waiye/hierarchy');
    if (res.data.code === 200) {
      cascaderOptions.value = res.data.tree || [];
    }
  } catch(e) {
    console.error(e);
  }
};"""

code = code.replace(old_fetch, new_fetch)

# 2. Update initial export settings so export tab also starts unselected
code = code.replace("const exportAreaText = ref('全椒县 (县级)');", "const exportAreaText = ref('');")
code = code.replace("const exportLevel = ref('county');", "const exportLevel = ref('');")

# 3. Enhance empty prompt when no group selected
old_empty_prompt = """        <div v-else-if="cascaderOptions.length > 0 && !currentGroupCode" class="empty-box">
          <van-icon name="guide-o" size="48" color="#1989fa" style="margin-bottom: 12px;" />
          <div style="font-size: 15px; color: #333;">请先在上方选择要核查的抽样组别</div>
        </div>"""

new_empty_prompt = """        <div v-else-if="cascaderOptions.length > 0 && !currentGroupCode" class="empty-box">
          <van-icon name="guide-o" size="48" color="#1989fa" style="margin-bottom: 12px;" />
          <div style="font-size: 15px; color: #333; margin-bottom: 6px;">请先在上方选择核查组别</div>
          <div style="font-size: 13px; color: #999;">点击上方“核查组别”选择抽样的乡镇、村、组，即可查看对应待核查地块清单</div>
        </div>"""

code = code.replace(old_empty_prompt, new_empty_prompt)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\frontend\src\views\WaiyeForm.vue", "w", encoding="utf-8") as f:
    f.write(code)

print("WaiyeForm.vue updated successfully.")