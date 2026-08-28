with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\frontend\src\views\WaiyeForm.vue", "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update template
old_phone = """              <div class="phone-info" v-if="item.lxdh">
                <van-icon name="phone-o" /> {{ item.lxdh }}
              </div>"""

new_phone = """              <a
                v-if="item.lxdh"
                :href="'tel:' + cleanPhone(item.lxdh)"
                class="phone-call-btn"
                title="点击直接拨打电话"
                @click.stop="handlePhoneClick(item.lxdh)"
              >
                <van-icon name="phone" color="#1989fa" />
                <span>{{ item.lxdh }}</span>
              </a>"""

code = code.replace(old_phone, new_phone)

# 2. Add helper functions in script
helpers = """const cleanPhone = (phone) => {
  if (!phone) return '';
  return String(phone).replace(/[^\\d+]/g, '');
};

const handlePhoneClick = (phone) => {
  if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(cleanPhone(phone)).catch(() => {});
  }
};
"""

# Insert before onMounted
pos_mounted = code.find("onMounted(async () => {")
code = code[:pos_mounted] + helpers + "\n" + code[pos_mounted:]

# 3. Update style
old_style = """.phone-info {
  font-size: 12px;
  color: #666;
}"""

new_style = """.phone-call-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #1989fa;
  background: #e8f3ff;
  border: 1px solid #d0e7ff;
  padding: 3px 9px;
  border-radius: 14px;
  text-decoration: none;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.phone-call-btn:active {
  background: #cbe3fd;
  transform: scale(0.96);
}"""

code = code.replace(old_style, new_style)

with open(r"G:\全椒县二轮延包\全椒县县级验收管理平台\frontend\src\views\WaiyeForm.vue", "w", encoding="utf-8") as f:
    f.write(code)

print("WaiyeForm.vue phone dial feature added.")