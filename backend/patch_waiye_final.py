with open("G:/全椒县二轮延包/全椒县县级验收管理平台/frontend/src/views/WaiyeForm.vue", "r", encoding="utf-8") as f:
    code = f.read()

sig_card_tpl = """
            <!-- 承包方代表手写签名区域 -->
            <div class="signature-box-wrap">
              <div class="sig-header">
                <span class="sig-title">承包方代表签名：</span>
                <van-tag v-if="item.signature_url" type="success" size="medium">已签名</van-tag>
                <van-tag v-else type="warning" size="medium">待签名</van-tag>
              </div>

              <div class="sig-card" @click="openSignModal(item)">
                <template v-if="item.signature_url">
                  <div class="sig-img-container">
                    <img :src="item.signature_url" alt="签名预览" class="sig-img" />
                  </div>
                  <div class="sig-action-hint">
                    <van-icon name="edit" /> 点击重新手写签名 / 放大
                  </div>
                </template>
                <template v-else>
                  <div class="sig-placeholder">
                    <van-icon name="edit" size="24" color="#1989fa" />
                    <div style="font-size: 13px; color: #1989fa; font-weight: 500; margin-top: 4px;">
                      点击进行手写签名 (代表: {{ item.cbfmc }})
                    </div>
                    <div style="font-size: 11px; color: #999; margin-top: 2px;">
                      签名将自动关联该承包方名下所有地块
                    </div>
                  </div>
                </template>
              </div>
            </div>
"""

pos_survey_end = code.find("</div>\r\n            </div>\r\n\r\n          </div>")
if pos_survey_end == -1:
    pos_survey_end = code.find("</div>\n            </div>\n\n          </div>")

idx_insert = pos_survey_end + 18
code = code[:idx_insert] + "\n" + sig_card_tpl + code[idx_insert:]

sig_modal_tpl = """
    <!-- ================= 手写签名大弹窗 ================= -->
    <van-popup
      v-model:show="showSignModal"
      round
      position="bottom"
      :style="{ height: '82vh' }"
      :close-on-click-overlay="false"
      @opened="onSignModalOpened"
    >
      <div class="sign-modal-content">
        <div class="modal-header">
          <div class="modal-title">承包方代表手写签名</div>
          <div class="modal-subtitle" v-if="currentSignContractor">
            代表姓名：<strong style="color:#1989fa;">{{ currentSignContractor.cbfmc }}</strong> | 
            缩略码：{{ currentSignContractor.cbfbm_short || currentSignContractor.cbfbm?.slice(-4) }}
          </div>
          <div class="modal-desc">
            请在下方框内手写签名，点击“确认保存签名”将自动关联保存为 PNG，并同步到该代表名下所有地块及导出的附件8中。
          </div>
        </div>

        <div class="canvas-wrapper" ref="canvasWrapperRef">
          <canvas
            ref="canvasRef"
            class="sign-canvas"
            @touchstart="handleTouchStart"
            @touchmove="handleTouchMove"
            @touchend="handleTouchEnd"
            @touchcancel="handleTouchEnd"
            @mousedown="handleMouseDown"
            @mousemove="handleMouseMove"
            @mouseup="handleMouseUp"
            @mouseleave="handleMouseUp"
          ></canvas>
        </div>

        <div class="modal-footer">
          <van-button round type="default" size="small" @click="clearCanvas" class="modal-btn">
            清空重写
          </van-button>
          <van-button round type="default" size="small" @click="closeSignModal" class="modal-btn">
            取消
          </van-button>
          <van-button round type="primary" size="small" :loading="savingSig" @click="saveSignature" class="modal-btn" style="flex: 1.6;">
            确认保存签名
          </van-button>
        </div>
      </div>
    </van-popup>
"""

pos_tpl_end = code.rfind("</van-tabs>")
code = code[:pos_tpl_end+11] + "\n" + sig_modal_tpl + code[pos_tpl_end+11:]

# Update import
code = code.replace(
    "import { ref, computed, onMounted, onUnmounted } from 'vue';",
    "import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';"
)

# Update state variables
sig_state_vars = """
// ================= 签名相关状态 =================
const showSignModal = ref(false);
const currentSignContractor = ref(null);
const canvasRef = ref(null);
const canvasWrapperRef = ref(null);
const savingSig = ref(false);
let isDrawing = false;
let hasDrawn = false;
let ctx = null;
"""
pos_vars = code.find("const exportingTownshipAtt8 = ref(false);")
code = code[:pos_vars+42] + "\n" + sig_state_vars + code[pos_vars+42:]

# Update loadGroupSamples mapping
code = code.replace(
    "survey_method: item.survey_method || '现场'\n      }));",
    "survey_method: item.survey_method || '现场',\n        signature_url: item.signature_url || ''\n      }));"
)
code = code.replace(
    "survey_method: item.survey_method || '现场'\r\n      }));",
    "survey_method: item.survey_method || '现场',\r\n        signature_url: item.signature_url || ''\r\n      }));"
)

sig_methods = """
// ================= 手写签名逻辑 =================

const openSignModal = (item) => {
  currentSignContractor.value = item;
  showSignModal.value = true;
};

const closeSignModal = () => {
  showSignModal.value = false;
  currentSignContractor.value = null;
};

const onSignModalOpened = () => {
  nextTick(() => {
    initCanvas();
  });
};

const initCanvas = () => {
  const canvas = canvasRef.value;
  const wrapper = canvasWrapperRef.value;
  if (!canvas || !wrapper) return;
  
  const rect = wrapper.getBoundingClientRect();
  const width = Math.max(rect.width, 300);
  const height = Math.max(rect.height, 220);
  const dpr = window.devicePixelRatio || 2;
  
  canvas.width = width * dpr;
  canvas.height = height * dpr;
  canvas.style.width = width + 'px';
  canvas.style.height = height + 'px';
  
  ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.lineWidth = 3.5;
  ctx.strokeStyle = '#000000';
  
  clearCanvas();
};

const clearCanvas = () => {
  const canvas = canvasRef.value;
  if (!canvas || !ctx) return;
  const dpr = window.devicePixelRatio || 2;
  ctx.clearRect(0, 0, canvas.width / dpr, canvas.height / dpr);
  hasDrawn = false;
};

const getCanvasPos = (e) => {
  const canvas = canvasRef.value;
  if (!canvas) return { x: 0, y: 0 };
  const rect = canvas.getBoundingClientRect();
  if (e.touches && e.touches.length > 0) {
    return {
      x: e.touches[0].clientX - rect.left,
      y: e.touches[0].clientY - rect.top
    };
  }
  return {
    x: e.clientX - rect.left,
    y: e.clientY - rect.top
  };
};

const handleTouchStart = (e) => {
  e.preventDefault();
  const pos = getCanvasPos(e);
  startDrawing(pos.x, pos.y);
};

const handleTouchMove = (e) => {
  e.preventDefault();
  if (!isDrawing) return;
  const pos = getCanvasPos(e);
  drawMove(pos.x, pos.y);
};

const handleTouchEnd = (e) => {
  e.preventDefault();
  stopDrawing();
};

const handleMouseDown = (e) => {
  const pos = getCanvasPos(e);
  startDrawing(pos.x, pos.y);
};

const handleMouseMove = (e) => {
  if (!isDrawing) return;
  const pos = getCanvasPos(e);
  drawMove(pos.x, pos.y);
};

const handleMouseUp = () => {
  stopDrawing();
};

const startDrawing = (x, y) => {
  if (!ctx) return;
  isDrawing = true;
  ctx.beginPath();
  ctx.moveTo(x, y);
};

const drawMove = (x, y) => {
  if (!ctx || !isDrawing) return;
  ctx.lineTo(x, y);
  ctx.stroke();
  hasDrawn = true;
};

const stopDrawing = () => {
  if (isDrawing && ctx) {
    ctx.closePath();
    isDrawing = false;
  }
};

const saveSignature = async () => {
  if (!hasDrawn) {
    showToast('请先在画板上手写签名');
    return;
  }
  const canvas = canvasRef.value;
  if (!canvas || !currentSignContractor.value) return;
  
  const dataUrl = canvas.toDataURL('image/png');
  const targetCbfbm = currentSignContractor.value.cbfbm;
  const targetCbfmc = currentSignContractor.value.cbfmc;
  
  savingSig.value = true;
  showLoadingToast({ message: '保存签名中...', forbidClick: true });
  try {
    const res = await axios.post('/api/waiye/save_signature', {
      cbfbm: targetCbfbm,
      cbfmc: targetCbfmc,
      signature_data: dataUrl
    });
    if (res.data.code === 200) {
      const newUrl = res.data.signature_url;
      for (const p of groupSamples.value) {
        if (p.cbfbm === targetCbfbm) {
          p.signature_url = newUrl;
        }
      }
      showToast({ type: 'success', message: `【${targetCbfmc}】代表手写签名保存成功！` });
      closeSignModal();
    } else {
      showToast(res.data.message || '签名保存失败');
    }
  } catch(e) {
    showToast('签名上传请求失败');
  } finally {
    savingSig.value = false;
    closeToast();
  }
};
"""

pos_tab2 = code.find("// ================= Tab 2 操作逻辑 =================")
code = code[:pos_tab2] + "\n" + sig_methods + "\n" + code[pos_tab2:]

sig_css = """
/* 签名区域样式 */
.signature-box-wrap {
  margin-top: 10px;
  background: #fafbfc;
  border: 1px solid #ebedf0;
  border-radius: 6px;
  padding: 10px 12px;
}

.sig-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.sig-title {
  font-size: 13px;
  font-weight: bold;
  color: #323233;
}

.sig-card {
  border: 1.5px dashed #c8e2fc;
  border-radius: 6px;
  background: #ffffff;
  padding: 8px 10px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}

.sig-card:active {
  background: #f0f7ff;
  border-color: #1989fa;
}

.sig-img-container {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.sig-img {
  max-height: 100%;
  max-width: 100%;
  object-fit: contain;
}

.sig-action-hint {
  font-size: 11px;
  color: #1989fa;
  margin-top: 4px;
}

.sig-placeholder {
  padding: 6px 0;
}

/* 手写签名全屏弹窗样式 */
.sign-modal-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 16px;
  box-sizing: border-box;
}

.modal-header {
  margin-bottom: 10px;
}

.modal-title {
  font-size: 17px;
  font-weight: bold;
  color: #323233;
  text-align: center;
  margin-bottom: 4px;
}

.modal-subtitle {
  font-size: 13px;
  color: #666;
  text-align: center;
  margin-bottom: 4px;
}

.modal-desc {
  font-size: 11px;
  color: #999;
  line-height: 1.4;
  background: #f7f8fa;
  padding: 6px 10px;
  border-radius: 4px;
  margin-top: 4px;
}

.canvas-wrapper {
  flex: 1;
  min-height: 220px;
  border: 2px solid #1989fa;
  border-radius: 8px;
  background: #fff;
  overflow: hidden;
  position: relative;
  touch-action: none;
}

.sign-canvas {
  width: 100%;
  height: 100%;
  display: block;
  cursor: crosshair;
}

.modal-footer {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.modal-btn {
  flex: 1;
}
"""

pos_style = code.rfind("</style>")
code = code[:pos_style] + "\n" + sig_css + code[pos_style:]

with open("G:/全椒县二轮延包/全椒县县级验收管理平台/frontend/src/views/WaiyeForm.vue", "w", encoding="utf-8") as f:
    f.write(code)

print("Successfully patched WaiyeForm.vue")