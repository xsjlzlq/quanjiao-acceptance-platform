<template>
  <div class="waiye">
    <van-nav-bar
      title="外业核查管理 (附表8/9)"
      left-arrow
      @click-left="$router.back()"
    />

    <van-tabs v-model:active="activeTab" sticky>
      <!-- ================= 模块一：外业核查 ================= -->
      <van-tab title="外业核查">
        <!-- 步骤1：选择抽样组别 -->
        <van-cell-group inset style="margin-top: 10px;">
          <van-field
            v-model="selectedGroupText"
            is-link
            readonly
            label="核查组别"
            placeholder="请选择已抽样的乡镇/村/组"
            @click="showCascader = true"
          />
          <van-popup v-model:show="showCascader" round position="bottom">
            <van-cascader
              v-model="cascaderValue"
              title="选择抽样组别"
              :options="cascaderOptions"
              @close="showCascader = false"
              @finish="onCascaderFinish"
            />
          </van-popup>
        </van-cell-group>

        <!-- 暂无抽样数据提示 -->
        <div v-if="cascaderOptions.length === 0" class="empty-box">
          <van-icon name="info-o" size="48" color="#ccc" style="margin-bottom: 12px;" />
          <div style="font-size: 15px; color: #666; margin-bottom: 8px;">数据库中暂无抽样数据</div>
          <div style="font-size: 13px; color: #999; margin-bottom: 16px;">请先在「任务与抽样」中执行抽样操作（方式一/二/三）</div>
          <van-button size="small" type="primary" round to="/tasks">去执行抽样</van-button>
        </div>

        <!-- 选中组别后展示数据与操作 -->
        <div v-if="currentGroupCode && groupSamples.length > 0">
          <!-- 组别得分与操作卡片 -->
          <div class="group-card">
            <div class="group-title">
              <div>
                <div>{{ currentTownshipName }} / {{ currentVillageName }} / {{ currentGroupName }}</div>
                <div style="font-size: 11px; font-weight: normal; color: #999; margin-top: 2px;">
                  <van-icon name="passed" color="#07c160" /> 实时静默保存 <span v-if="lastAutoSaveTime">(上次同步: {{ lastAutoSaveTime }})</span>
                </div>
              </div>
              <van-tag type="primary" size="medium">{{ groupSamples.length }} 块地</van-tag>
            </div>

            <div class="stats-grid">
              <div class="stat-item">
                <div class="stat-num text-danger">{{ totalErrorCount }}</div>
                <div class="stat-desc">错误项(X数量)</div>
              </div>
              <div class="stat-item">
                <div class="stat-num text-primary">{{ progScore }}</div>
                <div class="stat-desc">规范得分(20分)</div>
              </div>
              <div class="stat-item">
                <div class="stat-num text-success">{{ effectScore }}</div>
                <div class="stat-desc">满意度得分(10分)</div>
              </div>
            </div>

            <div class="btn-actions">
              
              <van-button v-if="hasPerm('waiye_export_att8')" size="small" type="success" round :loading="exportingGroupAtt8" @click="exportCurrentGroupAtt8">
                导出该组附件8_外业组检查记录表
              </van-button>
            </div>
          </div>

          <!-- 地块核查列表 -->
          <div style="padding: 10px 16px 4px 16px; font-size: 14px; font-weight: bold; color: #323233;">
            抽样地块清单（对附件8错误项点击打 X）：
          </div>

          <div 
            v-for="(grp, index) in groupedSamples" 
            :key="grp.cbfbm"
            class="parcel-card"
          >
            <!-- ================== 承包方层级信息 ================== -->
            <div class="parcel-header" style="background: #eef5fe; padding: 12px 14px; border-bottom: 1px solid #ebedf0; display: block;">
              <div class="farmer-info" style="margin-bottom: 6px;">
                <span class="index-badge" style="background: #1989fa;">{{ index + 1 }}</span>
                <span class="farmer-name" style="font-size: 16px;">{{ grp.cbfmc }}</span>
                <span class="code-tag">编码: {{ grp.cbfbm_short }}</span>
                <van-button size="mini" type="primary" plain round style="margin-left:auto; padding: 0 10px;" @click="showMembers(grp.parcels[0])">成员详情</van-button>
              </div>
              <div v-if="grp.lxdh" style="margin-top: 2px;">
                <a
                  :href="'tel:' + cleanPhone(grp.lxdh)"
                  class="phone-call-btn"
                  title="点击直接拨打电话"
                  @click.stop="handlePhoneClick(grp.lxdh)"
                  style="display: inline-flex; align-items: center; gap: 6px; font-size: 14px; color: #1989fa; text-decoration: none; padding: 4px 8px; background: rgba(25,137,250,0.08); border-radius: 4px;"
                >
                  <van-icon name="phone" color="#1989fa" size="16" />
                  <span>{{ grp.lxdh }}</span>
                </a>
              </div>
            </div>

            <div class="parcel-details" style="background: #fafcff;">
              <div class="detail-row">
                <span class="detail-label">合同总面积：</span>
                <span class="detail-val" style="color: #e6a23c; font-weight: bold; font-size: 15px;">{{ grp.total_scmj }} 亩</span>
                <span class="detail-label" style="margin-left: 12px; font-size: 12px; color: #999;">(汇总地块成果面积)</span>
              </div>
            </div>

            <!-- 承包方核查指标 -->
            <div class="check-section" style="background: #fafcff; padding-bottom: 10px;">
              <div class="section-tip">承包方核查指标（发现错误点击打 X）：</div>
              <div class="check-grid">
                <van-button 
                  size="mini" 
                  :type="grp.parcels[0].rights_correct === 'X' ? 'danger' : 'default'"
                  :plain="grp.parcels[0].rights_correct !== 'X'"
                  round
                  class="check-btn"
                  @click="toggleContractorError(grp, 'rights_correct')"
                >
                  {{ grp.parcels[0].rights_correct === 'X' ? '✗ 权属不正确(X)' : '权属调查是否正确' }}
                </van-button>
                <van-button 
                  size="mini" 
                  :type="grp.parcels[0].member_qualified === 'X' ? 'danger' : 'default'"
                  :plain="grp.parcels[0].member_qualified !== 'X'"
                  round
                  class="check-btn"
                  @click="toggleContractorError(grp, 'member_qualified')"
                >
                  {{ grp.parcels[0].member_qualified === 'X' ? '✗ 成员不符合(X)' : '家庭成员组织资格' }}
                </van-button>
                <van-button 
                  size="mini" 
                  :type="grp.parcels[0].self_signed === 'X' ? 'danger' : 'default'"
                  :plain="grp.parcels[0].self_signed !== 'X'"
                  round
                  class="check-btn"
                  @click="toggleContractorError(grp, 'self_signed')"
                >
                  {{ grp.parcels[0].self_signed === 'X' ? '✗ 非本人签名(X)' : '是否本人签名确认' }}
                </van-button>
                <van-button 
                  size="mini" 
                  :type="grp.parcels[0].phone_correct === 'X' ? 'danger' : 'default'"
                  :plain="grp.parcels[0].phone_correct !== 'X'"
                  round
                  class="check-btn"
                  @click="toggleContractorError(grp, 'phone_correct')"
                >
                  {{ grp.parcels[0].phone_correct === 'X' ? '✗ 联系电话(X)' : '联系电话是否正确' }}
                </van-button>
              </div>
            </div>

            <!-- 承包方满意度与调查方式 及 签名 -->
            <div class="survey-and-sig-row" style="background: #fafcff; border-bottom: 1px dashed #ebedf0; padding-bottom: 12px;">
              <div class="survey-col">
                <div class="survey-item">
                  <span class="survey-label">是否满意：</span>
                  <!-- 由于所有 parcels 同步，我们可以直接绑定到 grp.parcels[0] -->
                  <van-radio-group v-model="grp.parcels[0].satisfaction" direction="horizontal" @change="(v) => { grp.parcels.forEach(p => p.satisfaction = v); saveAllSilent(); }">
                    <van-radio name="满意" icon-size="14px">满意</van-radio>
                    <van-radio name="不满意" icon-size="14px">不满意</van-radio>
                  </van-radio-group>
                </div>
                <div class="survey-item" style="margin-top: 8px;">
                  <span class="survey-label">抽样方式：</span>
                  <van-radio-group v-model="grp.parcels[0].survey_method" direction="horizontal" @change="(v) => { grp.parcels.forEach(p => p.survey_method = v); saveAllSilent(); }">
                    <van-radio name="现场" icon-size="14px">现场</van-radio>
                    <van-radio name="电话" icon-size="14px">电话</van-radio>
                  </van-radio-group>
                </div>
              </div>

              <div class="sig-col">
                <div class="signature-box-wrap-inline" @click="openSignModal(grp.parcels[0])">
                  <template v-if="grp.parcels[0].signature_url">
                    <div class="sig-img-container-inline">
                      <img :src="grp.parcels[0].signature_url" alt="签名预览" class="sig-img-inline" />
                    </div>
                    <div class="sig-action-hint-inline">
                      <van-icon name="edit" /> 重签
                    </div>
                  </template>
                  <template v-else>
                    <div class="sig-placeholder-inline">
                      <van-icon name="edit" size="20" color="#1989fa" />
                      <div class="sig-text-inline">点击签名</div>
                    </div>
                  </template>
                </div>
              </div>
            </div>

            <!-- ================== 地块层级信息 ================== -->
            <div v-for="(item, pIndex) in grp.parcels" :key="item.id" class="parcel-sub-card" style="padding: 12px 14px; border-bottom: 1px solid #f2f3f5;">
              <div class="parcel-details" style="padding: 0;">
                <div class="detail-row">
                  <span class="detail-label" style="color:#1989fa; font-weight:bold;">地块 {{ pIndex + 1 }}</span>
                  <span class="detail-label" style="margin-left: 8px;">名称：</span>
                  <span class="detail-val">{{ item.dkmc || '未命名地块' }}</span>
                  <span class="detail-label" style="margin-left: 12px;">简码：</span>
                  <span class="detail-val">{{ item.dkbm_short || item.dkbm?.slice(-5) || '-' }}</span>
                </div>
                <div class="detail-row" style="margin-top: 6px;">
                  <span class="detail-label">成果面积：</span>
                  <span class="detail-val" style="color: #666;">{{ item.scmj }} 亩</span>
                  <van-button size="mini" type="success" plain round style="margin-left:8px; padding: 0 6px;" @click="showBounds(item)">四至详情</van-button>
                </div>
              </div>

              <!-- 地块级核查指标 -->
              <div class="check-section" style="padding: 8px 0 0 0;">
                <div class="section-tip" style="padding-left:0; font-size: 12px;">地块核查指标（错误打 X）：</div>
                <div class="check-grid" style="grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));">
                  <van-button 
                    size="mini" 
                    :type="item.area_acknowledged === 'X' ? 'danger' : 'default'"
                    :plain="item.area_acknowledged !== 'X'"
                    round
                    class="check-btn"
                    @click="toggleError(item, 'area_acknowledged')"
                  >
                    {{ item.area_acknowledged === 'X' ? '✗ 面积不认可(X)' : '是否认可确权面积' }}
                  </van-button>

                  <van-button 
                    size="mini" 
                    :type="item.bound_correct === 'X' ? 'danger' : 'default'"
                    :plain="item.bound_correct !== 'X'"
                    round
                    class="check-btn"
                    @click="toggleError(item, 'bound_correct')"
                  >
                    {{ item.bound_correct === 'X' ? '✗ 四至不正确(X)' : '地块四至是否正确' }}
                  </van-button>

                  <van-button 
                    size="mini" 
                    :type="item.self_verified === 'X' ? 'danger' : 'default'"
                    :plain="item.self_verified !== 'X'"
                    round
                    class="check-btn"
                    @click="toggleError(item, 'self_verified')"
                  >
                    {{ item.self_verified === 'X' ? '✗ 非本人核实(X)' : '是否本人核实地块' }}
                  </van-button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div v-else-if="cascaderOptions.length > 0 && !currentGroupCode" class="empty-box">
          <van-icon name="guide-o" size="48" color="#1989fa" style="margin-bottom: 12px;" />
          <div style="font-size: 15px; color: #333; margin-bottom: 6px;">请先在上方选择核查组别</div>
          <div style="font-size: 13px; color: #999;">点击上方“核查组别”选择抽样的乡镇、村、组，即可查看对应待核查地块清单</div>
        </div>
      </van-tab>

      <!-- ================= 模块二：附件导出 ================= -->
      <van-tab title="附件导出">
        <!-- 导出层级下拉选择面板 -->
        <van-cell-group inset style="margin-top: 10px;">
          <van-field
            v-model="exportAreaText"
            is-link
            readonly
            label="导出范围"
            placeholder="请选择县级或乡镇"
            @click="showExportPicker = true"
          />
          <van-popup v-model:show="showExportPicker" round position="bottom">
            <van-picker
              title="选择导出层级与单位"
              :columns="exportPickerColumns"
              @cancel="showExportPicker = false"
              @confirm="onExportPickerConfirm"
            />
          </van-popup>
        </van-cell-group>

        <!-- 场景A：县级导出（导出附件9） -->
        <div v-if="exportLevel === 'county'" class="export-panel">
          <div class="panel-header">
            <div class="panel-title">全椒县县级自查外业汇总</div>
            <van-tag type="warning" size="medium">县级层级</van-tag>
          </div>
          <div class="panel-desc">
            汇总全县所有已完成外业抽样与打X核查的乡镇、村、组数据，生成全县外业组检查得分表（附件9）。
          </div>

          <div style="margin-top: 20px;">
            <van-button 
              v-if="hasPerm('waiye_export_att9')"
              round 
              block 
              type="warning" 
              icon="description"
              :loading="exportingAtt9" 
              @click="onExportAtt9"
            >
              导出附件9 全县外业检查得分表
            </van-button>
          </div>
        </div>

        <!-- 场景B：乡镇级导出（导出附件8） -->
        <div v-else-if="exportLevel === 'township'" class="export-panel">
          <div class="panel-header">
            <div class="panel-title">{{ exportTownshipName }} 外业核查记录表</div>
            <van-tag type="success" size="medium">乡镇层级</van-tag>
          </div>
          
          <div class="panel-desc">
            导出写入了该镇实际外业核查内容（含打X错误项、满意度、发包方得分公式）的附件8文档。
          </div>

          <!-- 批量导出该镇全部附件8 -->
          <div style="margin-top: 16px;">
            <van-button 
              round 
              block 
              type="success" 
              icon="down"
              :loading="exportingTownshipAtt8" 
              @click="onExportTownshipAllAtt8"
            >
              导出 {{ exportTownshipName }} 全部附件8 (共 {{ currentTownshipGroupList.length }} 组)
            </van-button>
          </div>

          <!-- 各组列表明细与单独导出 -->
          <div v-if="currentTownshipGroupList.length > 0" style="margin-top: 20px;">
            <div style="font-size: 14px; font-weight: bold; color: #323233; margin-bottom: 10px;">
              该镇抽样组清单（支持单组下载）：
            </div>
            <van-cell-group inset style="margin: 0;">
              <van-cell 
                v-for="(grp, idx) in currentTownshipGroupList" 
                :key="idx"
                :title="`${grp.village_name} ${grp.group_name}`"
                :label="`地块: ${grp.parcel_count}块 | 错误: ${grp.error_count}项 | 得分: ${grp.prog_score}分`"
                center
              >
                <template #right-icon>
                  <van-button 
                    size="small" 
                    type="primary" 
                    plain 
                    round
                    @click="onExportSingleGroupAtt8(grp)"
                  >
                    下载附件8
                  </van-button>
                </template>
              </van-cell>
            </van-cell-group>
          </div>
          <div v-else class="empty-tip">
            该乡镇下暂无抽样数据，请先在「任务与抽样」中抽样。
          </div>
        </div>

        <div v-else style="text-align:center; padding: 60px 20px; color:#999;">
          <van-icon name="filter-o" size="48" color="#ccc" style="margin-bottom: 12px;" />
          <div style="font-size: 15px;">请先在上方选择导出范围（全椒县或乡镇）</div>
        </div>
      </van-tab>
    </van-tabs>

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

  </div>

    <!-- 成员详情与四至弹窗 -->
    <van-popup v-model:show="membersDialogVisible" round position="bottom" style="max-height: 70%">
      <div style="padding: 16px; font-size: 16px; font-weight: bold; text-align: center;">{{ currentMembersTitle }}</div>
      <div v-if="membersLoading" style="text-align: center; padding: 20px;">
        <van-loading type="spinner" />
      </div>
      <div v-else style="padding: 0 16px 20px 16px;">
        <van-cell-group inset v-if="membersList.length > 0">
          <van-cell v-for="(m, i) in membersList" :key="i">
            <template #title>
              <div style="font-weight: bold; font-size: 15px;">{{ m.name }} <van-tag type="primary" style="margin-left: 6px;">{{ relationDict[m.relation] || m.relation || '未知' }}</van-tag></div>
              <div style="font-size: 12px; color: #666; margin-top: 4px;">证件: {{ m.id_no }}</div>
            </template>
          </van-cell>
        </van-cell-group>
        <van-empty v-else description="暂无家庭成员数据" />
      </div>
    </van-popup>

    <van-popup v-model:show="boundsDialogVisible" round position="bottom">
      <div style="padding: 16px; font-size: 16px; font-weight: bold; text-align: center;">{{ currentBoundsTitle }}</div>
      <div v-if="boundsLoading" style="text-align: center; padding: 20px;">
        <van-loading type="spinner" />
      </div>
      <div v-else style="padding: 0 16px 20px 16px;">
        <van-cell-group inset>
          <van-cell title="东至" :value="boundsData.east || '-'" />
          <van-cell title="西至" :value="boundsData.west || '-'" />
          <van-cell title="南至" :value="boundsData.south || '-'" />
          <van-cell title="北至" :value="boundsData.north || '-'" />
        </van-cell-group>
      </div>
    </van-popup>

</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue';
import { hasPerm } from '../utils/auth';
import { showToast, showLoadingToast, closeToast } from 'vant';
import axios from 'axios';

const activeTab = ref(0);

// ================= Tab 1: 外业核查 =================
const showCascader = ref(false);
const cascaderValue = ref('');
const cascaderOptions = ref([]);

const selectedGroupText = ref('');
const currentTownshipName = ref('');
const currentVillageName = ref('');
const currentGroupName = ref('');
const currentGroupCode = ref('');

const groupSamples = ref([]);

const groupedSamples = computed(() => {
  const map = new Map();
  for (const item of groupSamples.value) {
    if (!map.has(item.cbfbm)) {
      map.set(item.cbfbm, {
        cbfmc: item.cbfmc,
        cbfbm: item.cbfbm,
        cbfbm_short: item.cbfbm_short || item.cbfbm?.slice(-4),
        lxdh: item.lxdh,
        parcels: [],
        total_scmj: 0
      });
    }
    const grp = map.get(item.cbfbm);
    grp.parcels.push(item);
    grp.total_scmj += Number(item.scmj || 0);
  }
  // Format total_scmj to 2 decimals
  for (const grp of map.values()) {
    grp.total_scmj = grp.total_scmj.toFixed(2);
  }
  return Array.from(map.values());
});

const toggleContractorError = async (grp, field) => {
  if (!grp.parcels.length) return;
  const isError = grp.parcels[0][field] === 'X';
  const newVal = isError ? '' : 'X';
  for (const p of grp.parcels) {
    p[field] = newVal;
  }
  await saveAllSilent();
};

const saving = ref(false);
const exportingGroupAtt8 = ref(false);

// ================= Tab 2: 附件导出 =================
const showExportPicker = ref(false);
const exportAreaText = ref('');
const exportLevel = ref(''); // 'county' | 'township'
const exportTownshipName = ref('');

const exportPickerColumns = ref([]);
const townshipsSummaryList = ref([]);
const exportingAtt9 = ref(false);
const exportingTownshipAtt8 = ref(false);


// ================= 签名相关状态 =================
const showSignModal = ref(false);
const currentSignContractor = ref(null);
const canvasRef = ref(null);
const canvasWrapperRef = ref(null);
const savingSig = ref(false);
let isDrawing = false;
let hasDrawn = false;
let ctx = null;


const AUTO_SAVE_KEY = 'auto_save_settings';
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
        survey_method: item.survey_method,
        phone_correct: item.phone_correct
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


// 家庭成员与四至详情逻辑
const membersDialogVisible = ref(false);
const membersLoading = ref(false);
const currentMembersTitle = ref('家庭成员详情');
const membersList = ref([]);

const boundsDialogVisible = ref(false);
const boundsLoading = ref(false);
const currentBoundsTitle = ref('四至详情');
const boundsData = ref({});

const relationDict = {
        '01': "本人",
        '02': "户主",
        '10': "配偶",
        '11': "夫",
        '12': "妻",
        '20': "子",
        '21': "独生子",
        '22': "长子",
        '23': "次子",
        '24': "三子",
        '25': "四子",
        '26': "五子",
        '27': "养子或继子",
        '28': "女婿",
        '29': "其他儿子",
        '30': "女",
        '31': "独生女",
        '32': "长女",
        '33': "次女",
        '34': "三女",
        '35': "四女",
        '36': "五女",
        '37': "养女或继女",
        '38': "儿媳",
        '39': "其他女儿",
        '40': "孙子、孙女或外孙子、外孙女",
        '41': "孙子",
        '42': "孙女",
        '43': "外孙子",
        '44': "外孙女",
        '45': "孙媳妇或外孙媳妇",
        '46': "孙女婿或外孙女婿",
        '47': "曾孙子或外曾孙子",
        '48': "曾孙女或外曾孙女",
        '49': "其他孙子、孙女或外孙子、外孙女",
        '50': "父母",
        '51': "父亲",
        '52': "母亲",
        '53': "公公",
        '54': "婆婆",
        '55': "岳父",
        '56': "岳母",
        '57': "继父或养父",
        '58': "继母或养母",
        '59': "其他父母关系",
        '60': "祖父母或外祖父母",
        '61': "祖父",
        '62': "祖母",
        '63': "外祖父",
        '64': "外祖母",
        '65': "配偶的祖父母或外祖父母",
        '66': "曾祖父",
        '67': "曾祖母",
        '68': "配偶的曾祖父或外曾祖父",
        '69': "他祖父母或外祖父母关系",
        '70': "兄弟姐妹",
        '71': "兄",
        '72': "嫂",
        '73': "弟",
        '74': "弟媳",
        '75': "姐姐",
        '76': "姐夫",
        '77': "妹妹",
        '78': "妹夫",
        '79': "其他兄弟姐妹",
        '80': "其他",
        '81': "伯父",
        '82': "伯母",
        '83': "叔父",
        '84': "婶母",
        '85': "舅父",
        '86': "舅母",
        '87': "姨父",
        '88': "姨母",
        '89': "姑父",
        '90': "姑母",
        '91': "堂兄弟、堂姐妹",
        '92': "表兄弟、表姐妹",
        '93': "侄子",
        '94': "侄女",
        '95': "外甥",
        '96': "外甥女",
        '97': "其他亲属",
        '98': "非亲属",
        '99': "其他关系",
        '100': "其他关系",
    };

const showMembers = async (item) => {
  if (!item.cbfbm) {
    showToast('该条目无有效承包方编码');
    return;
  }
  currentMembersTitle.value = item.cbfmc + ' 的家庭成员';
  membersDialogVisible.value = true;
  membersLoading.value = true;
  membersList.value = [];
  try {
    const res = await axios.get('/api/waiye/family_members?cbfbm=' + item.cbfbm);
    if (res.data.code === 200) {
      membersList.value = res.data.data;
    }
  } catch(e) {
    showToast('获取家庭成员失败');
  } finally {
    membersLoading.value = false;
  }
};

const showBounds = async (item) => {
  if (!item.dkbm) {
    showToast('该条目无有效地块编码');
    return;
  }
  currentBoundsTitle.value = (item.dkmc || '未命名地块') + ' - 四至详情';
  boundsDialogVisible.value = true;
  boundsLoading.value = true;
  boundsData.value = {};
  try {
    const res = await axios.get('/api/waiye/parcel_bounds?dkbm=' + item.dkbm);
    if (res.data.code === 200) {
      boundsData.value = res.data.data;
    }
  } catch(e) {
    showToast('获取四至信息失败');
  } finally {
    boundsLoading.value = false;
  }
};


const cleanPhone = (phone) => {
  if (!phone) return '';
  return String(phone).replace(/[^\d+]/g, '');
};

const handlePhoneClick = (phone) => {
  if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(cleanPhone(phone)).catch(() => {});
  }
};

onMounted(async () => {
  await fetchWaiyeHierarchy();
  await fetchTownshipsSummary();
  await initExportPickerColumns();
  loadAutoSaveConfig();
  if (autoSaveConfig.value.enabled) {
    const ms = autoSaveConfig.value.interval * 60 * 1000;
    autoSaveTimer = setInterval(silentAutoSave, ms);
  }
});

onUnmounted(() => {
  if (autoSaveTimer) {
    clearInterval(autoSaveTimer);
    autoSaveTimer = null;
  }
  if (autoSaveConfig.value.enabled) {
    silentAutoSave();
  }
});

const initExportPickerColumns = async () => {
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
            text: `${name} (县级 - 导出附件9)`,
            value: codeStr.substring(0, 6),
            level: 'county'
          };
        } else if (codeStr.endsWith('00000') && codeStr.length === 14) {
          tsList.push({
            text: `${item.name} (乡镇级 - 导出附件8)`,
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
    console.error('Failed to load export picker columns', e);
  }
};

const fetchWaiyeHierarchy = async () => {
  try {
    const res = await axios.get('/api/waiye/hierarchy');
    if (res.data.code === 200) {
      cascaderOptions.value = res.data.tree || [];
    }
  } catch(e) {
    console.error(e);
  }
};

const fetchTownshipsSummary = async () => {
  try {
    const res = await axios.get('/api/waiye/townships_summary');
    if (res.data.code === 200) {
      townshipsSummaryList.value = res.data.data || [];
    }
  } catch(e) {
    console.error(e);
  }
};

const currentTownshipGroupList = computed(() => {
  if (exportLevel.value !== 'township' || !exportTownshipName.value) return [];
  const found = townshipsSummaryList.value.find(t => t.township_name === exportTownshipName.value);
  return found ? found.groups : [];
});

const onCascaderFinish = ({ selectedOptions }) => {
  showCascader.value = false;
  if (!selectedOptions || selectedOptions.length < 3) return;
  const ts = selectedOptions[0];
  const vill = selectedOptions[1];
  const grp = selectedOptions[2];
  selectGroup(ts.township_name, vill.village_name, grp.group_name, grp.group_code);
};

const selectGroup = async (tName, vName, gName, gCode) => {
  currentTownshipName.value = tName;
  currentVillageName.value = vName;
  currentGroupName.value = gName;
  currentGroupCode.value = gCode;
  selectedGroupText.value = `${tName} / ${vName} / ${gName}`;
  cascaderValue.value = gCode;
  
  await loadGroupSamples(gCode, tName, vName, gName);
};

const loadGroupSamples = async (gCode, tName, vName, gName) => {
  showLoadingToast({ message: '加载地块清单...', forbidClick: true });
  try {
    const res = await axios.get('/api/waiye/group_samples', {
      params: {
        group_code: gCode,
        township_name: tName,
        village_name: vName,
        group_name: gName
      }
    });
    if (res.data.code === 200) {
      groupSamples.value = res.data.data.map(item => {
        const phoneVal = (item.lxdh || '').toString().trim();
        const phoneErr = item.phone_correct ? item.phone_correct : (!phoneVal ? 'X' : '');
        return {
          ...item,
          area_acknowledged: item.area_acknowledged || '',
          rights_correct: item.rights_correct || '',
          bound_correct: item.bound_correct || '',
          member_qualified: item.member_qualified || '',
          self_verified: item.self_verified || '',
          self_signed: item.self_signed || '',
          satisfaction: item.satisfaction || '满意',
          survey_method: item.survey_method || '现场',
          signature_url: item.signature_url || '',
          phone_correct: phoneErr
        };
      });
    }
  } catch(e) {
    showToast('加载地块记录失败');
  } finally {
    closeToast();
  }
};

const toggleError = async (item, field) => {
  item[field] = item[field] === 'X' ? '' : 'X';
  await saveAllSilent();
};

const totalErrorCount = computed(() => {
  let count = 0;
  for (const grp of groupedSamples.value) {
    const first = grp.parcels[0];
    if (first.rights_correct === 'X') count++;
    if (first.member_qualified === 'X') count++;
    if (first.self_signed === 'X') count++;
    if (first.phone_correct === 'X') count++;
    for (const p of grp.parcels) {
      if (p.area_acknowledged === 'X') count++;
      if (p.bound_correct === 'X') count++;
      if (p.self_verified === 'X') count++;
    }
  }
  return count;
});

const progScore = computed(() => {
  const score = Math.max(20.0 - totalErrorCount.value * 0.5, 0.0);
  return score.toFixed(1);
});

const effectScore = computed(() => {
  if (groupedSamples.value.length === 0) return '10.0';
  const satisfiedCount = groupedSamples.value.filter(grp => grp.parcels[0].satisfaction === '满意').length;
  const score = (satisfiedCount / groupedSamples.value.length) * 10.0;
  return score.toFixed(1);
});

const saveAllSilent = async () => {
  if (groupSamples.value.length === 0) return;
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
        survey_method: item.survey_method,
        phone_correct: item.phone_correct
      }))
    };
    await axios.post('/api/waiye/save_records', payload);
    const now = new Date();
    lastAutoSaveTime.value = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
  } catch (e) {
    console.warn('静默保存失败', e);
  }
};

const saveAll = async () => {
  if (groupSamples.value.length === 0) return;
  saving.value = true;
  showLoadingToast({ message: '正在保存...', forbidClick: true });
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
        survey_method: item.survey_method,
        phone_correct: item.phone_correct
      }))
    };
    const res = await axios.post('/api/waiye/save_records', payload);
    if (res.data.code === 200) {
      showToast({ type: 'success', message: '外业核查状态已保存到数据库！' });
      await fetchTownshipsSummary();
    } else {
      showToast(res.data.message || '保存失败');
    }
  } catch(e) {
    showToast('保存请求失败');
  } finally {
    saving.value = false;
    closeToast();
  }
};

const triggerDownload = (url) => {
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', '');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

const exportCurrentGroupAtt8 = async () => {
  if (!currentGroupCode.value) return;
  exportingGroupAtt8.value = true;
  showLoadingToast({ message: '生成附件8...', forbidClick: true });
  try {
    // Auto-save state
    await axios.post('/api/waiye/save_records', {
      records: groupSamples.value.map(item => ({
        id: item.id,
        area_acknowledged: item.area_acknowledged,
        rights_correct: item.rights_correct,
        bound_correct: item.bound_correct,
        member_qualified: item.member_qualified,
        self_verified: item.self_verified,
        self_signed: item.self_signed,
        satisfaction: item.satisfaction,
        survey_method: item.survey_method,
        phone_correct: item.phone_correct
      }))
    });

    const res = await axios.post('/api/export_waiye_att8', {
      township_name: currentTownshipName.value,
      village_name: currentVillageName.value,
      group_name: currentGroupName.value,
      group_code: currentGroupCode.value
    });

    if (res.data.code === 200 && res.data.url) {
      showToast({ type: 'success', message: '附件8已生成，正在下载...' });
      triggerDownload(res.data.url);
    } else {
      showToast(res.data.message || '生成失败');
    }
  } catch(e) {
    showToast('生成请求失败');
  } finally {
    exportingGroupAtt8.value = false;
  }
};



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
      await saveAllSilent();
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

// ================= Tab 2 操作逻辑 =================

const onExportPickerConfirm = ({ selectedOptions }) => {
  showExportPicker.value = false;
  if (!selectedOptions || selectedOptions.length === 0) return;
  const opt = selectedOptions[0];
  exportAreaText.value = opt.text;
  exportLevel.value = opt.level;
  exportTownshipName.value = opt.townshipName || '';
};

const onExportAtt9 = async () => {
  exportingAtt9.value = true;
  showLoadingToast({ message: '汇总全县得分生成附件9...', forbidClick: true });
  try {
    const res = await axios.get('/api/export_waiye_att9');
    if (res.data.code === 200 && res.data.url) {
      showToast({ type: 'success', message: '附件9已生成，正在下载...' });
      triggerDownload(res.data.url);
    } else {
      showToast(res.data.message || '生成失败');
    }
  } catch(e) {
    showToast('生成附件9失败');
  } finally {
    exportingAtt9.value = false;
  }
};

const onExportTownshipAllAtt8 = async () => {
  if (!exportTownshipName.value) return;
  exportingTownshipAtt8.value = true;
  showLoadingToast({ message: `生成 ${exportTownshipName.value} 附件8...`, forbidClick: true });
  try {
    const res = await axios.post('/api/export_waiye_att8', {
      township_name: exportTownshipName.value
    });
    if (res.data.code === 200 && res.data.urls) {
      showToast({ type: 'success', message: `已生成 ${res.data.count} 份附件8，正在下载...` });
      for (const u of res.data.urls) {
        triggerDownload(u);
      }
    } else {
      showToast(res.data.message || '生成失败');
    }
  } catch(e) {
    showToast('批量导出失败');
  } finally {
    exportingTownshipAtt8.value = false;
  }
};

const onExportSingleGroupAtt8 = async (grp) => {
  showLoadingToast({ message: '生成附件8...', forbidClick: true });
  try {
    const res = await axios.post('/api/export_waiye_att8', {
      township_name: exportTownshipName.value,
      village_name: grp.village_name,
      group_name: grp.group_name,
      group_code: grp.group_code
    });
    if (res.data.code === 200 && res.data.url) {
      showToast({ type: 'success', message: '附件8已生成，正在下载...' });
      triggerDownload(res.data.url);
    } else {
      showToast(res.data.message || '生成失败');
    }
  } catch(e) {
    showToast('导出失败');
  }
};
</script>

<style scoped>
.waiye {
  padding-bottom: 60px;
  background-color: #f7f8fa;
  min-height: 100vh;
}

.empty-box {
  text-align: center;
  padding: 60px 20px;
}

.empty-tip {
  text-align: center;
  padding: 30px 16px;
  color: #999;
  font-size: 13px;
}

.group-card {
  margin: 12px 16px;
  background: #fff;
  border-radius: 8px;
  padding: 14px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.group-title {
  font-size: 15px;
  font-weight: bold;
  color: #323233;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.stats-grid {
  display: flex;
  justify-content: space-around;
  background: #f9f9fb;
  border-radius: 6px;
  padding: 10px 0;
  margin-bottom: 12px;
}

.stat-item {
  text-align: center;
}

.stat-num {
  font-size: 18px;
  font-weight: 800;
}

.stat-desc {
  font-size: 12px;
  color: #888;
  margin-top: 2px;
}

.btn-actions {
  display: flex;
  gap: 10px;
}

.parcel-card {
  margin: 10px 16px;
  background: #fff;
  border-radius: 8px;
  padding: 14px 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03);
}

.parcel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f2f2f2;
  padding-bottom: 8px;
  margin-bottom: 8px;
}

.farmer-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.index-badge {
  display: inline-block;
  width: 20px;
  height: 20px;
  line-height: 20px;
  text-align: center;
  background: #1989fa;
  color: #fff;
  font-size: 12px;
  font-weight: bold;
  border-radius: 10px;
}

.farmer-name {
  font-size: 15px;
  font-weight: bold;
  color: #323233;
}

.code-tag {
  font-size: 12px;
  color: #999;
  background: #f5f5f5;
  padding: 1px 4px;
  border-radius: 3px;
}

.phone-call-btn {
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
}

.parcel-details {
  font-size: 13px;
  color: #555;
  margin-bottom: 10px;
  background: #fafafa;
  padding: 6px 10px;
  border-radius: 4px;
}

.detail-row {
  margin: 3px 0;
}

.detail-label {
  color: #999;
}

.detail-val {
  color: #333;
}

.check-section {
  margin-bottom: 10px;
}

.section-tip {
  font-size: 12px;
  color: #888;
  margin-bottom: 6px;
}

.check-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.check-btn {
  font-size: 11px;
  padding: 0 4px;
  height: 28px;
}

.survey-and-sig-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px dashed #eee;
  padding-top: 10px;
  margin-top: 4px;
}

.survey-col {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.survey-item {
  display: flex;
  align-items: center;
  font-size: 13px;
}

.survey-label {
  color: #666;
  width: 70px;
}

.sig-col {
  width: 120px;
  margin-left: 10px;
}

.signature-box-wrap-inline {
  background: #fafbfc;
  border: 1px solid #ebedf0;
  border-radius: 6px;
  padding: 6px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 54px;
}

.sig-img-container-inline {
  width: 100%;
  height: 36px;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  background: white;
  border: 1px solid #f0f0f0;
  border-radius: 4px;
}

.sig-img-inline {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.sig-action-hint-inline {
  font-size: 11px;
  color: #1989fa;
  margin-top: 4px;
}

.sig-placeholder-inline {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #1989fa;
}

.sig-text-inline {
  font-size: 11px;
  margin-top: 4px;
  font-weight: 500;
}

.empty-box {
  text-align: center;
  padding: 60px 20px;
}

.empty-tip {
  text-align: center;
  padding: 30px 16px;
  color: #999;
  font-size: 13px;
}

.group-card {
  margin: 12px 16px;
  background: #fff;
  border-radius: 8px;
  padding: 14px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.group-title {
  font-size: 15px;
  font-weight: bold;
  color: #323233;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.stats-grid {
  display: flex;
  justify-content: space-around;
  background: #f9f9fb;
  border-radius: 6px;
  padding: 10px 0;
  margin-bottom: 12px;
}

.stat-item {
  text-align: center;
}

.stat-num {
  font-size: 18px;
  font-weight: 800;
}

.stat-desc {
  font-size: 12px;
  color: #888;
  margin-top: 2px;
}

.btn-actions {
  display: flex;
  gap: 10px;
}

.parcel-card {
  margin: 10px 16px;
  background: #fff;
  border-radius: 8px;
  padding: 14px 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.03);
}

.parcel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #f2f2f2;
  padding-bottom: 8px;
  margin-bottom: 8px;
}

.farmer-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.index-badge {
  display: inline-block;
  width: 20px;
  height: 20px;
  line-height: 20px;
  text-align: center;
  background: #1989fa;
  color: #fff;
  font-size: 12px;
  font-weight: bold;
  border-radius: 10px;
}

.farmer-name {
  font-size: 15px;
  font-weight: bold;
  color: #323233;
}

.code-tag {
  font-size: 12px;
  color: #999;
  background: #f5f5f5;
  padding: 1px 4px;
  border-radius: 3px;
}

.phone-call-btn {
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
}

.parcel-details {
  font-size: 13px;
  color: #555;
  margin-bottom: 10px;
  background: #fafafa;
  padding: 6px 10px;
  border-radius: 4px;
}

.detail-row {
  margin: 3px 0;
}

.detail-label {
  color: #999;
}

.detail-val {
  color: #333;
}

.check-section {
  margin-bottom: 10px;
}

.section-tip {
  font-size: 12px;
  color: #888;
  margin-bottom: 6px;
}

.check-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.check-btn {
  font-size: 11px;
  padding: 0 4px;
  height: 28px;
}

.survey-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
  border-top: 1px dashed #eee;
  padding-top: 8px;
}

.survey-item {
  display: flex;
  align-items: center;
  font-size: 13px;
}

.survey-label {
  color: #666;
  width: 70px;
  flex-shrink: 0;
}

/* 导出面板样式 */
.export-panel {
  margin: 12px 16px;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.panel-title {
  font-size: 16px;
  font-weight: bold;
  color: #323233;
}

.panel-desc {
  font-size: 13px;
  color: #666;
  line-height: 1.5;
}

.text-danger { color: #ee0a24; }
.text-primary { color: #1989fa; }
.text-success { color: #07c160; }


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
</style>