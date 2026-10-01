<template>
  <div class="neiye">
    <van-nav-bar title="内业核查表单 (附表6/7)" left-text="返回" left-arrow @click-left="$router.back()" />

    <!-- Area Selection (County & Townships only) -->
    <van-cell-group inset style="margin-top: 10px;">
      <van-field
        v-model="selectedAreaName"
        is-link
        readonly
        label="核查对象"
        placeholder="请选择县级或抽样村"
        @click="showPicker = true"
      />
      <van-popup v-model:show="showPicker" round position="bottom">
        <van-picker
          title="选择核查对象"
          :columns="pickerColumns"
          @cancel="showPicker = false"
          @confirm="onPickerConfirm"
        />
      </van-popup>
    </van-cell-group>

    <!-- Top Action Bar when Area Selected -->
    <div v-if="selectedAreaName" class="action-card">
      <div class="score-display">
        <div>
          <div class="score-label">{{ selectedAreaName }} 内业得分：</div>
          <div style="font-size: 11px; font-weight: normal; color: #999; margin-top: 2px;">
            <van-icon name="passed" color="#07c160" /> 实时保存 <span v-if="lastAutoSaveTime">(上次同步: {{ lastAutoSaveTime }})</span>
          </div>
        </div>
        <div class="score-val">{{ totalScore }} <span class="score-max">/ {{ (selectedAreaLevel === 'county' || selectedAreaLevel === 'township') ? 25 : 70 }}分</span></div>
      </div>
      <div class="btn-group">
        
        
        
          <van-button size="small" type="primary" round :loading="exportingVoucher" @click="onExportVoucher">
            导出凭证记录
          </van-button>
          <van-button size="small" type="danger" plain round :loading="exportingFeedback" @click="onExportFeedbackSummary">
            导出问题反馈记录表汇总
          </van-button>
<!-- Village/Township Exports -->
        <template v-if="selectedAreaLevel !== 'county'">
          <van-button v-if="hasPerm('neiye_export_att6')" size="small" type="success" round :loading="exporting6" @click="onExportAtt6">
            {{ selectedAreaLevel === 'township' ? '导出附件6 检查记录表（1/4、4/4）' : '导出附件6 检查记录表（1/4~4/4）' }}
          </van-button>
        </template>

        

<!-- County Exports -->
        <template v-if="selectedAreaLevel === 'county'">
          <van-button v-if="hasPerm('neiye_export_att6')" size="small" type="success" round :loading="exporting6" @click="onExportAtt6">
            导出附件6 检查记录表（1/4、4/4）
          </van-button>
          <van-button v-if="hasPerm('neiye_export_att7')" size="small" type="warning" round :loading="exporting7" @click="onExportAtt7">
            导出附件7 检查得分表
          </van-button>
        </template>
      </div>

      <div style="margin-top: 10px; display: flex; gap: 20px; font-size: 14px; align-items: center; padding-top: 8px; border-top: 1px dashed #eee;">
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="white-space: nowrap;">检查者:</span>
          <van-field v-model="form.jcz_name" placeholder="请输入" style="width: 100px; border: 1px solid #ebedf0; border-radius: 4px; padding: 4px 8px;" @blur="silentAutoSave" />
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
          <span style="white-space: nowrap;">复核者:</span>
          <van-field v-model="form.fhz_name" placeholder="请输入" style="width: 100px; border: 1px solid #ebedf0; border-radius: 4px; padding: 4px 8px;" @blur="silentAutoSave" />
        </div>
      </div>
    </div>

    <!-- Main Tabs -->
    <van-tabs v-model:active="activeTab" sticky v-if="selectedAreaName" style="margin-top: 10px;">
      <!-- Tab 1: 机制运行 (15分) - Available for both County & Township -->
      <van-tab title="机制运行(15分)">
        <van-cell-group inset v-for="grp in MECH_GROUPS" :key="grp.field" :title="grp.title" style="margin-top: 10px;">
          <van-checkbox-group v-model="form[grp.field]">
            <template v-for="opt in grp.options" :key="opt.label">
              <van-cell :title="`${opt.label} (${opt.desc})`" clickable @click="toggle(grp.field, opt.label)">
                <template #right-icon>
                  <van-checkbox :name="opt.label" @click.stop.prevent="toggle(grp.field, opt.label)" />
                </template>
              </van-cell>
              <!-- 凭证上传区 -->
              <div v-if="form[grp.field] && form[grp.field].includes(opt.label)" class="evidence-box">
                <div class="evidence-header">
                  <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                  <div class="uploader-btns">
                    <van-uploader :after-read="(f) => onUploadEvidence(f, opt.label)" accept="image/*">
                      <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                    </van-uploader>
                  </div>
                </div>
                <div v-if="getEvidenceList(opt.label).length > 0" class="evidence-imgs">
                  <div v-for="(img, idx) in getEvidenceList(opt.label)" :key="idx" class="img-thumb">
                    <img :src="img.url" @click="previewEvidence(img.url)" />
                    <span class="del-btn" @click.stop.prevent="removeEvidence(opt.label, idx)">×</span>
                  </div>
                </div>
              </div>
            </template>
          </van-checkbox-group>
          <div class="group-tip">{{ grp.tip }}</div>
        </van-cell-group>
      </van-tab>

      <!-- Village Tabs: Only visible if village (Township only checks 机制运行 15分 like County) -->
      <template v-if="selectedAreaLevel === 'village'">
        <!-- Tab 2: 程序规范 (30分) -->
        <van-tab title="程序规范(30分)">
          <van-cell-group inset v-for="grp in PROG_GROUPS" :key="grp.field" :title="grp.title" style="margin-top: 10px;">
            <van-checkbox-group v-model="form[grp.field]">
              <template v-for="opt in grp.options" :key="opt.label">
                <van-cell :title="`${opt.label} (${opt.desc})`" clickable @click="toggle(grp.field, opt.label)">
                  <template #right-icon>
                    <van-checkbox :name="opt.label" @click.stop.prevent="toggle(grp.field, opt.label)" />
                  </template>
                </van-cell>
                <!-- 凭证上传区 -->
                <div v-if="form[grp.field] && form[grp.field].includes(opt.label)" class="evidence-box">
                  <div class="evidence-header">
                    <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                    <div class="uploader-btns">
                      <van-uploader :after-read="(f) => onUploadEvidence(f, opt.label)" accept="image/*">
                        <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                      </van-uploader>
                    </div>
                  </div>
                  <div v-if="getEvidenceList(opt.label).length > 0" class="evidence-imgs">
                    <div v-for="(img, idx) in getEvidenceList(opt.label)" :key="idx" class="img-thumb">
                      <img :src="img.url" @click="previewEvidence(img.url)" />
                      <span class="del-btn" @click.stop.prevent="removeEvidence(opt.label, idx)">×</span>
                    </div>
                  </div>
                </div>
              </template>
            </van-checkbox-group>
            <div class="group-tip">{{ grp.tip }}</div>
          </van-cell-group>
        </van-tab>

        <!-- Tab 3: 政策落实 (15分) -->
        <van-tab title="政策落实(15分)">
          <!-- 1. “大稳定、小调整”落实情况 (3分) -->
          <van-cell-group inset :title="POLICY_CHECKBOX_1.title" style="margin-top: 10px;">
            <van-checkbox-group v-model="form[POLICY_CHECKBOX_1.field]">
              <template v-for="opt in POLICY_CHECKBOX_1.options" :key="opt.label">
                <van-cell :title="`${opt.label} (${opt.desc})`" clickable @click="toggle(POLICY_CHECKBOX_1.field, opt.label)">
                  <template #right-icon>
                    <van-checkbox :name="opt.label" @click.stop.prevent="toggle(POLICY_CHECKBOX_1.field, opt.label)" />
                  </template>
                </van-cell>
                <div v-if="form[POLICY_CHECKBOX_1.field] && form[POLICY_CHECKBOX_1.field].includes(opt.label)" class="evidence-box">
                  <div class="evidence-header">
                    <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                    <div class="uploader-btns">
                      <van-uploader :after-read="(f) => onUploadEvidence(f, opt.label)" accept="image/*">
                        <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                      </van-uploader>
                    </div>
                  </div>
                  <div v-if="getEvidenceList(opt.label).length > 0" class="evidence-imgs">
                    <div v-for="(img, idx) in getEvidenceList(opt.label)" :key="idx" class="img-thumb">
                      <img :src="img.url" @click="previewEvidence(img.url)" />
                      <span class="del-btn" @click.stop.prevent="removeEvidence(opt.label, idx)">×</span>
                    </div>
                  </div>
                </div>
              </template>
            </van-checkbox-group>
            <div class="group-tip">{{ POLICY_CHECKBOX_1.tip }}</div>
          </van-cell-group>

          <!-- 2. 保障土地承包权益 (3分) - 步进器 -->
          <van-cell-group inset title="2. 保障土地承包权益 (3分)" style="margin-top: 10px;">
            <template v-for="st in POLICY_STEPPERS_2" :key="st.field">
              <van-field :name="st.field" :label="st.label">
                <template #input>
                  <div class="stepper-wrap">
                    <van-stepper v-model="form[st.field]" min="0" step="1" @change="(val) => onStepperChange(st.field, st.label, val)" />
                    <span class="stepper-unit">起</span>
                  </div>
                </template>
              </van-field>
              <div v-if="form[st.field] > 0" class="evidence-box">
                <div class="evidence-header">
                  <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                  <div class="uploader-btns">
                    <van-uploader :after-read="(f) => onUploadEvidence(f, st.label)" accept="image/*">
                      <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                    </van-uploader>
                  </div>
                </div>
                <div v-if="getEvidenceList(st.label).length > 0" class="evidence-imgs">
                  <div v-for="(img, idx) in getEvidenceList(st.label)" :key="idx" class="img-thumb">
                    <img :src="img.url" @click="previewEvidence(img.url)" />
                    <span class="del-btn" @click.stop.prevent="removeEvidence(st.label, idx)">×</span>
                  </div>
                </div>
              </div>
            </template>
            <div class="group-tip">注：发现一起扣1分，扣完3分为止。</div>
          </van-cell-group>

          <!-- 3. 依法收回消亡户承包地 (3分) - 步进器 -->
          <van-cell-group inset title="3. 依法收回消亡户承包地 (3分)" style="margin-top: 10px;">
            <template v-for="st in POLICY_STEPPERS_3" :key="st.field">
              <van-field :name="st.field" :label="st.label">
                <template #input>
                  <div class="stepper-wrap">
                    <van-stepper v-model="form[st.field]" min="0" step="1" @change="(val) => onStepperChange(st.field, st.label, val)" />
                    <span class="stepper-unit">起</span>
                  </div>
                </template>
              </van-field>
              <div v-if="form[st.field] > 0" class="evidence-box">
                <div class="evidence-header">
                  <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                  <div class="uploader-btns">
                    <van-uploader :after-read="(f) => onUploadEvidence(f, st.label)" accept="image/*">
                      <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                    </van-uploader>
                  </div>
                </div>
                <div v-if="getEvidenceList(st.label).length > 0" class="evidence-imgs">
                  <div v-for="(img, idx) in getEvidenceList(st.label)" :key="idx" class="img-thumb">
                    <img :src="img.url" @click="previewEvidence(img.url)" />
                    <span class="del-btn" @click.stop.prevent="removeEvidence(st.label, idx)">×</span>
                  </div>
                </div>
              </div>
            </template>
            <div class="group-tip">注：发现一起扣1分，扣完3分为止。</div>
          </van-cell-group>

          <!-- 4. 严格机动地和新增耕地管理 (3分) -->
          <van-cell-group inset :title="POLICY_CHECKBOX_4.title" style="margin-top: 10px;">
            <van-checkbox-group v-model="form[POLICY_CHECKBOX_4.field]">
              <template v-for="opt in POLICY_CHECKBOX_4.options" :key="opt.label">
                <van-cell :title="`${opt.label} (${opt.desc})`" clickable @click="toggle(POLICY_CHECKBOX_4.field, opt.label)">
                  <template #right-icon>
                    <van-checkbox :name="opt.label" @click.stop.prevent="toggle(POLICY_CHECKBOX_4.field, opt.label)" />
                  </template>
                </van-cell>
                <div v-if="form[POLICY_CHECKBOX_4.field] && form[POLICY_CHECKBOX_4.field].includes(opt.label)" class="evidence-box">
                  <div class="evidence-header">
                    <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                    <div class="uploader-btns">
                      <van-uploader :after-read="(f) => onUploadEvidence(f, opt.label)" accept="image/*">
                        <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                      </van-uploader>
                    </div>
                  </div>
                  <div v-if="getEvidenceList(opt.label).length > 0" class="evidence-imgs">
                    <div v-for="(img, idx) in getEvidenceList(opt.label)" :key="idx" class="img-thumb">
                      <img :src="img.url" @click="previewEvidence(img.url)" />
                      <span class="del-btn" @click.stop.prevent="removeEvidence(opt.label, idx)">×</span>
                    </div>
                  </div>
                </div>
              </template>
            </van-checkbox-group>
            <div class="group-tip">{{ POLICY_CHECKBOX_4.tip }}</div>
          </van-cell-group>

          <!-- 5. 从严掌握确权确股不确地 (3分) -->
          <van-cell-group inset :title="POLICY_CHECKBOX_5.title" style="margin-top: 10px;">
            <van-checkbox-group v-model="form[POLICY_CHECKBOX_5.field]">
              <template v-for="opt in POLICY_CHECKBOX_5.options" :key="opt.label">
                <van-cell :title="`${opt.label} (${opt.desc})`" clickable @click="toggle(POLICY_CHECKBOX_5.field, opt.label)">
                  <template #right-icon>
                    <van-checkbox :name="opt.label" @click.stop.prevent="toggle(POLICY_CHECKBOX_5.field, opt.label)" />
                  </template>
                </van-cell>
                <div v-if="form[POLICY_CHECKBOX_5.field] && form[POLICY_CHECKBOX_5.field].includes(opt.label)" class="evidence-box">
                  <div class="evidence-header">
                    <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                    <div class="uploader-btns">
                      <van-uploader :after-read="(f) => onUploadEvidence(f, opt.label)" accept="image/*">
                        <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                      </van-uploader>
                    </div>
                  </div>
                  <div v-if="getEvidenceList(opt.label).length > 0" class="evidence-imgs">
                    <div v-for="(img, idx) in getEvidenceList(opt.label)" :key="idx" class="img-thumb">
                      <img :src="img.url" @click="previewEvidence(img.url)" />
                      <span class="del-btn" @click.stop.prevent="removeEvidence(opt.label, idx)">×</span>
                    </div>
                  </div>
                </div>
              </template>
            </van-checkbox-group>
            <div class="group-tip">{{ POLICY_CHECKBOX_5.tip }}</div>
          </van-cell-group>
        </van-tab>
      </template>

      <!-- Tab 4: 工作成效 (10分) - Available for County, Township, and Village -->
      <van-tab title="工作成效(10分)">
        <van-cell-group inset v-for="grp in EFFECT_GROUPS" :key="grp.field" :title="grp.title" style="margin-top: 10px;">
          <van-checkbox-group v-model="form[grp.field]">
            <template v-for="opt in grp.options" :key="opt.label">
              <van-cell :title="`${opt.label} (${opt.desc})`" clickable @click="toggle(grp.field, opt.label)">
                <template #right-icon>
                  <van-checkbox :name="opt.label" @click.stop.prevent="toggle(grp.field, opt.label)" />
                </template>
              </van-cell>
              <div v-if="form[grp.field] && form[grp.field].includes(opt.label)" class="evidence-box">
                <div class="evidence-header">
                  <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                  <div class="uploader-btns">
                    <van-uploader :after-read="(f) => onUploadEvidence(f, opt.label)" accept="image/*">
                      <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                    </van-uploader>
                  </div>
                </div>
                <div v-if="getEvidenceList(opt.label).length > 0" class="evidence-imgs">
                  <div v-for="(img, idx) in getEvidenceList(opt.label)" :key="idx" class="img-thumb">
                    <img :src="img.url" @click="previewEvidence(img.url)" />
                    <span class="del-btn" @click.stop.prevent="removeEvidence(opt.label, idx)">×</span>
                  </div>
                </div>
              </div>
            </template>
          </van-checkbox-group>
          <div class="group-tip">{{ grp.tip }}</div>
        </van-cell-group>
      </van-tab>
    </van-tabs>

    <!-- Empty prompt if no area selected -->
    <div v-if="!selectedAreaName" style="text-align:center; padding: 60px 20px; color:#999;">
      <van-icon name="info-o" size="48" color="#ccc" style="margin-bottom:12px;" />
      <div style="font-size: 15px;">请先在上方选择核查对象（全县或乡镇）</div>
    </div>
  </div>

    
</template>

<script setup>
import { ref, nextTick, computed, onMounted, onUnmounted } from 'vue';
import { hasPerm } from '../utils/auth';
import { showToast, showLoadingToast, closeToast, showImagePreview } from 'vant';
import axios from 'axios';

const activeTab = ref(0);
const showPicker = ref(false);
const selectedAreaName = ref('');
const selectedAreaCode = ref('');
const selectedAreaLevel = ref('');
const selectedTownshipName = ref('');
const selectedVillageName = ref('');

const saving = ref(false);
const exporting6 = ref(false);
const exporting7 = ref(false);
const exportingFeedback = ref(false);

const pickerColumns = ref([]);

// ── 表单配置（严格匹配附件6最新标准） ─────────────────────────
const MECH_GROUPS = [
  {
    field: 'mech_1',
    title: '1. 延包方案与分工 (2分)',
    tip: '注：发现任何一项扣2分。',
    options: [
      { label: '未制定方案', desc: '扣2分' },
      { label: '方案未盖章或非红头', desc: '扣2分' },
      { label: '直接套用上级方案', desc: '扣2分' },
      { label: '分工不明确', desc: '扣2分' },
      { label: '制定程序不合法', desc: '扣2分' },
      { label: '方案缺少', desc: '扣2分' }
    ]
  },
  {
    field: 'mech_2',
    title: '2. 经费保障 (10分)',
    tip: '注：支付不及时扣4分；支付不规范扣4分；政府未明确兜底经费的扣2分。',
    options: [
      { label: '支付不规范', desc: '扣4分' },
      { label: '支付不及时', desc: '扣4分' },
      { label: '经费没有县级兜底', desc: '扣2分' }
    ]
  },
  {
    field: 'mech_3',
    title: '3. 宣传 (2分)',
    tip: '注：没有宣传材料不得分（扣2分）；宣传材料无效或途径单一按规定扣分。',
    options: [
      { label: '没有宣传材料', desc: '扣2分' },
      { label: '宣传材料无效', desc: '扣2分' },
      { label: '宣传途径单一', desc: '扣2分' }
    ]
  },
  {
    field: 'mech_4',
    title: '4. 培训 (1分)',
    tip: '注：发现一项扣0.5分，扣完1分为止。',
    options: [
      { label: '没有培训材料', desc: '扣0.5分' },
      { label: '没有分批次培训', desc: '扣0.5分' },
      { label: '培训材料不齐全', desc: '扣0.5分' },
      { label: '培训未覆盖县乡村组', desc: '扣0.5分' },
      { label: '培训材料无效', desc: '扣0.5分' }
    ]
  }
];

const PROG_GROUPS = [
  {
    field: 'prog_1',
    title: '1. 成立机构 (5分)',
    tip: '注：发现任何一项扣5分。',
    options: [
      { label: '未召开村民会议', desc: '扣5分' },
      { label: '未选举产生理事会', desc: '扣5分' },
      { label: '未公示理事会名单', desc: '扣5分' },
      { label: '公示时间不足3天', desc: '扣5分' },
      { label: '参会人数不足法定数量', desc: '扣5分' },
      { label: '违规召开村民会议', desc: '扣5分' },
      { label: '理事会成员非本集体经济组织', desc: '扣5分' }
    ]
  },
  {
    field: 'prog_2',
    title: '2. 摸底核实 (5分)',
    tip: '注：发现一项扣每户0.5分，扣完5分为止。',
    options: [
      { label: '没有进行摸底', desc: '扣0.5分' },
      { label: '摸底表农户未签署', desc: '扣0.5分' },
      { label: '摸底表中没有表达延包意愿', desc: '扣0.5分' },
      { label: '摸底表其它签署不齐全', desc: '扣0.5分' },
      { label: '特殊人员摸底不清或未统计', desc: '扣0.5分' },
      { label: '户变化未统计', desc: '扣0.5分' },
      { label: '矛盾纠纷未登记', desc: '扣0.5分' },
      { label: '矛盾纠纷未登记不完整', desc: '扣0.5分' },
      { label: '本级矛盾纠纷没有处理记录', desc: '扣0.5分' },
      { label: '承包地变化未摸清', desc: '扣0.5分' },
      { label: '没有应确尽确', desc: '扣0.5分' },
      { label: '没有统计新增耕地、机动地', desc: '扣0.5分' },
      { label: '没有统计补充确权', desc: '扣0.5分' },
      { label: '没有统计新增确权确亩不确界或未说明', desc: '扣0.5分' },
      { label: '没有统计小调整或未说明', desc: '扣0.5分' },
      { label: '各类统计资料没有封面', desc: '扣0.5分' },
      { label: '各类统计资料没有签章', desc: '扣0.5分' },
      { label: '各类统计资料统计不正确', desc: '扣0.5分' },
      { label: '摸底与其它材料时间矛盾', desc: '扣0.5分' }
    ]
  },
  {
    field: 'prog_3',
    title: '3. 制定方案 (5分)',
    tip: '注：发现任意一项扣5分。',
    options: [
      { label: '没有延包方案草案', desc: '扣5分' },
      { label: '没有延包方案', desc: '扣5分' },
      { label: '延包方案未上报', desc: '扣5分' },
      { label: '延包方案未公示', desc: '扣5分' },
      { label: '未召开会议讨论延包方案', desc: '扣5分' },
      { label: '延包方案上报与通过会议时间顺序不正确', desc: '扣5分' },
      { label: '延包方案与工作方案混淆', desc: '扣5分' },
      { label: '理事会与工作领导小组混淆', desc: '扣5分' }
    ]
  },
  {
    field: 'prog_4',
    title: '4. 调查公示 (2分)',
    tip: '注：发现公示时间不足15天或没有公示材料直接扣2分；发现其它任意一项扣0.5分，扣完2分为止。',
    options: [
      { label: '没有公示材料', desc: '扣2分' },
      { label: '没有公示或公示不足15天', desc: '扣2分' },
      { label: '公示结果未确认（归户表没签署）', desc: '扣0.5分' },
      { label: '各类资料不齐全', desc: '扣0.5分' },
      { label: '各类资料制作粗糙', desc: '扣0.5分' },
      { label: '各类资料签署不规范', desc: '扣0.5分' },
      { label: '权属证明材料不齐全', desc: '扣0.5分' },
      { label: '其它证明材料不齐全', desc: '扣0.5分' },
      { label: '各类资料间时间顺序混乱', desc: '扣0.5分' }
    ]
  },
  {
    field: 'prog_5',
    title: '5. 签订合同 (3分)',
    tip: '注：发现任意一项扣3分。',
    options: [
      { label: '合同版本格式不正确', desc: '扣3分' },
      { label: '合同网签率未达到95%', desc: '扣3分' },
      { label: '没有地块示意图', desc: '扣3分' }
    ]
  },
  {
    field: 'prog_6',
    title: '6. 完善证书 (5分)',
    tip: '注：前五项发现任意一项扣5分；后两项发现一项扣0.5分，扣完5分为止。',
    options: [
      { label: '未进行信息共享', desc: '扣5分' },
      { label: '未与不动产登记部门有序衔接', desc: '扣5分' },
      { label: '承包地块间重叠', desc: '扣5分' },
      { label: '承包地块与宅基地重叠', desc: '扣5分' },
      { label: '承包地块与其它自然资源部门要求的要素重叠', desc: '扣5分' },
      { label: '缺少登记要件', desc: '扣0.5分' },
      { label: '资料格式不符合登记要求', desc: '扣0.5分' }
    ]
  },
  {
    field: 'prog_7',
    title: '7. 资料归档 (5分)',
    tip: '注：前三项发现任意一项扣5分；后六项发现任意一项扣1分，扣完5分为止。',
    options: [
      { label: '档案整理第三方无涉密档案整理资质', desc: '扣5分' },
      { label: '没有进行档案验收', desc: '扣5分' },
      { label: '档案验收不符合相关标准', desc: '扣5分' },
      { label: '档案资料涂改多处', desc: '扣1分' },
      { label: '档案资料缺少主体内容', desc: '扣1分' },
      { label: '档案资料缺少佐证内容', desc: '扣1分' },
      { label: '档案资料背考表签署不正确', desc: '扣1分' },
      { label: '档案资料存在大量漏签署', desc: '扣1分' },
      { label: '档案资料姓名错误未检查', desc: '扣1分' }
    ]
  }
];

const POLICY_CHECKBOX_1 = {
  field: 'policy_1',
  title: '1. “大稳定、小调整”落实情况 (3分)',
  tip: '注：发现任何一项扣1分，扣完3分为止。',
  options: [
    { label: '小调整比率过大或手续不齐全', desc: '扣1分' },
    { label: '打乱重分', desc: '扣1分' },
    { label: '违法调整或收回承包地', desc: '扣1分' },
    { label: '没有小调整统计资料或说明', desc: '扣1分' }
  ]
};

const POLICY_STEPPERS_2 = [
  { field: 'policy_2_1', label: '未保障特殊群体权益' },
  { field: 'policy_2_2', label: '未保障无地户权益' },
  { field: 'policy_2_3', label: '没有统计（关注）特殊群体' }
];

const POLICY_STEPPERS_3 = [
  { field: 'policy_3_1', label: '没有应收尽收' },
  { field: 'policy_3_2', label: '采用不正当方式隐匿消亡户' },
  { field: 'policy_3_3', label: '违规处置消亡土地' },
  { field: 'policy_3_4', label: '没有统计消亡户' },
  { field: 'policy_3_5', label: '没有分清实际消亡户和伪消亡户' }
];

const POLICY_CHECKBOX_4 = {
  field: 'policy_4',
  title: '4. 严格机动地和新增耕地管理 (3分)',
  tip: '注：发现一项扣0.5分，扣完3分为止。',
  options: [
    { label: '机动地、新增耕地处置不当', desc: '扣0.5分' },
    { label: '机动地比率过高', desc: '扣0.5分' },
    { label: '未统计机动地和新增耕地', desc: '扣0.5分' }
  ]
};

const POLICY_CHECKBOX_5 = {
  field: 'policy_5',
  title: '5. 从严掌握确权确股不确地 (3分)',
  tip: '注：发现一项扣0.5分，扣完3分为止。',
  options: [
    { label: '违背农户意愿强行推进', desc: '扣0.5分' },
    { label: '确权确股不确地手续不齐全', desc: '扣0.5分' },
    { label: '没有统计新增确权确亩不确界', desc: '扣0.5分' }
  ]
};

const EFFECT_GROUPS = [
  {
    field: 'effect_1',
    title: '加强风险防范 (10分)',
    tip: '注：发现任何一项扣1分，扣完10分为止。',
    options: [
      { label: '未建立矛盾纠纷处置机制', desc: '扣1分' },
      { label: '未建立舆情处置办法', desc: '扣1分' },
      { label: '没有矛盾纠纷处理台账', desc: '扣1分' },
      { label: '矛盾纠纷处理台账填写不规范', desc: '扣1分' },
      { label: '没有本级处理的矛盾纠纷处理记录', desc: '扣1分' }
    ]
  }
];



const form = ref({
  mech_1: [], mech_2: [], mech_3: [], mech_4: [],
  prog_1: [], prog_2: [], prog_3: [], prog_4: [], prog_5: [], prog_6: [], prog_7: [],
  policy_1: [], policy_2_1: 0, policy_2_2: 0, policy_2_3: 0,
  policy_3_1: 0, policy_3_2: 0, policy_3_3: 0, policy_3_4: 0, policy_3_5: 0,
  policy_4: [], policy_5: [],
  effect_1: [], jcz_name: '', fhz_name: '', jcz_sign: '', fhz_sign: '',
  evidences: {}
});


const AUTO_SAVE_KEY = 'auto_save_settings';
const autoSaveConfig = ref({ enabled: false, interval: 5 });
const lastAutoSaveTime = ref('');
let autoSaveTimer = null;

const loadAutoSaveConfig = () => {
  try {
    const raw = localStorage.getItem(AUTO_SAVE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      autoSaveConfig.value = {
        enabled: parsed.enabled === true,
        interval: Number(parsed.interval) > 0 ? Math.max(1, Math.round(Number(parsed.interval))) : 5
      };
    } else {
      autoSaveConfig.value = { enabled: false, interval: 5 };
    }
  } catch (e) {
    autoSaveConfig.value = { enabled: false, interval: 5 };
  }
};

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

onMounted(async () => {
  showLoadingToast({ message: '加载中...', forbidClick: true });
  try {
    const res = await axios.get('/api/neiye/townships');
    if (res.data.code === 200) {
      const county = res.data.county;
      const villages = res.data.villages || [];
      const townships = res.data.townships || [];
      
      pickerColumns.value = [];
      if (county) {
        pickerColumns.value.push({ text: `${county.name} (县级 - 机制与成效)`, value: county.code, level: 'county' });
      }
      
      // 1. 增加乡镇级选项：供录入各乡镇本级的“机制运行(15分)与工作成效(10分)”
      if (townships.length > 0) {
        pickerColumns.value.push(
          ...townships.map(t => ({
            text: `${t.name} (乡镇级 - 机制与成效)`,
            value: t.code,
            level: 'township',
            townshipName: t.name,
            villageName: ''
          }))
        );
      }

      // 2. 行政村级选项：供录入各抽样行政村的内业检查 (70分)
      if (villages.length > 0) {
        pickerColumns.value.push(
          ...villages.map(v => ({
            text: v.full_title || `${v.township_name} - ${v.name}`,
            value: v.code,
            level: 'village',
            townshipName: v.township_name,
            villageName: v.name
          }))
        );
      }
    }
  } catch(e) {
    showToast('获取区域层级失败');
  } finally {
    closeToast();
  }
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

const onPickerConfirm = ({ selectedOptions }) => {
  showPicker.value = false;
  if (!selectedOptions || selectedOptions.length === 0) return;
  const opt = selectedOptions[0];
  selectedAreaName.value = opt.text;
  selectedAreaCode.value = opt.value;
  selectedAreaLevel.value = opt.level;
  selectedTownshipName.value = opt.townshipName || '';
  selectedVillageName.value = opt.villageName || '';
  
  if (selectedAreaLevel.value === 'county' || selectedAreaLevel.value === 'township') {
    activeTab.value = 0;
  }
  
  loadSavedData(opt.value);
};

const loadSavedData = async (code) => {
  showLoadingToast({ message: '加载评分...', forbidClick: true });
  try {
    const res = await axios.get('/api/get_neiye?qsdwdm=' + code);
    if (res.data.code === 200 && res.data.data && res.data.data.form_data) {
      const fd = res.data.data.form_data;
      // Compat: if mech_4 was stored as count in older version
      if (typeof fd.mech_4 === 'number') {
        fd.mech_4 = [];
      }
      form.value = {
        mech_1: fd.mech_1 || [],
        mech_2: fd.mech_2 || [],
        mech_3: fd.mech_3 || [],
        mech_4: fd.mech_4 || [],
        prog_1: fd.prog_1 || [],
        prog_2: fd.prog_2 || [],
        prog_3: fd.prog_3 || [],
        prog_4: fd.prog_4 || [],
        prog_5: fd.prog_5 || [],
        prog_6: fd.prog_6 || [],
        prog_7: fd.prog_7 || [],
        policy_1: fd.policy_1 || [],
        policy_2_1: fd.policy_2_1 || 0,
        policy_2_2: fd.policy_2_2 || 0,
        policy_2_3: fd.policy_2_3 || 0,
        policy_3_1: fd.policy_3_1 || 0,
        policy_3_2: fd.policy_3_2 || 0,
        policy_3_3: fd.policy_3_3 || 0,
        policy_3_4: fd.policy_3_4 || 0,
        policy_3_5: fd.policy_3_5 || 0,
        policy_4: fd.policy_4 || [],
        policy_5: fd.policy_5 || [],
        effect_1: fd.effect_1 || [],
        jcz_name: fd.jcz_name || '',
        fhz_name: fd.fhz_name || '',
        evidences: fd.evidences || {}
      };
      showToast('已加载历史保存数据');
    } else {
      // reset form
      form.value = {
        mech_1: [], mech_2: [], mech_3: [], mech_4: [],
        prog_1: [], prog_2: [], prog_3: [], prog_4: [], prog_5: [], prog_6: [], prog_7: [],
        policy_1: [], policy_2_1: 0, policy_2_2: 0, policy_2_3: 0,
        policy_3_1: 0, policy_3_2: 0, policy_3_3: 0, policy_3_4: 0, policy_3_5: 0,
        policy_4: [], policy_5: [],
        effect_1: [], jcz_name: '', fhz_name: '', evidences: {}
      };
    }
  } catch(e) {
    console.error(e);
  } finally {
    closeToast();
  }
};

const toggle = async (group, name) => {
  const list = form.value[group];
  const idx = list.indexOf(name);
  if (idx > -1) {
    // 检查是否有关联凭证，若有凭证则拦截并提示先删除凭证
    const evidences = form.value.evidences && form.value.evidences[name];
    if (evidences && evidences.length > 0) {
      showToast({ type: 'fail', message: '已上传凭证，请先删除该项凭证后再取消勾选！' });
      return;
    }
    list.splice(idx, 1);
  } else {
    list.push(name);
  }
  await silentAutoSave();
};

const onStepperChange = async (field, name, newVal) => {
  if (newVal === 0) {
    const evidences = form.value.evidences && form.value.evidences[name];
    if (evidences && evidences.length > 0) {
      showToast({ type: 'fail', message: '已上传凭证，请先删除该项凭证后再清零！' });
      form.value[field] = 1;
      return;
    }
  }
  await silentAutoSave();
};

const totalScore = computed(() => {
  // 1. 机制运行 (满分15)
  let d_m1 = form.value.mech_1.length > 0 ? 2.0 : 0.0;
  let d_m2 = 0.0;
  for (const opt of form.value.mech_2) {
    if (opt.includes('支付不规范')) d_m2 += 4.0;
    else if (opt.includes('支付不及时')) d_m2 += 4.0;
    else if (opt.includes('兜底')) d_m2 += 2.0;
  }
  d_m2 = Math.min(d_m2, 10.0);
  let d_m3 = form.value.mech_3.length > 0 ? 2.0 : 0.0;
  let d_m4 = Math.min(form.value.mech_4.length * 0.5, 1.0);
  
  let deduct_mech = Math.min(d_m1 + d_m2 + d_m3 + d_m4, 15.0);
  let score_mech = Math.max(15.0 - deduct_mech, 0.0);

  // 4. 工作成效 (满分10)
  let deduct_effect = Math.min(form.value.effect_1.length * 1.0, 10.0);
  let score_effect = Math.max(10.0 - deduct_effect, 0.0);

  if (selectedAreaLevel.value === 'county' || selectedAreaLevel.value === 'township') {
    return Number((score_mech + score_effect).toFixed(1));
  }

  // 2. 程序规范 (满分30)
  let d_p1 = form.value.prog_1.length > 0 ? 5.0 : 0.0;
  let d_p2 = Math.min(form.value.prog_2.length * 0.5, 5.0);
  let d_p3 = form.value.prog_3.length > 0 ? 5.0 : 0.0;
  
  let d_p4 = 0.0;
  if (form.value.prog_4.some(x => x.includes('没有公示材料') || x.includes('不足15天'))) {
    d_p4 = 2.0;
  } else {
    d_p4 = Math.min(form.value.prog_4.length * 0.5, 2.0);
  }
  let d_p5 = form.value.prog_5.length > 0 ? 3.0 : 0.0;
  
  let d_p6 = 0.0;
  if (form.value.prog_6.some(x => ['未进行信息共享', '未与不动产登记部门有序衔接', '承包地块间重叠', '承包地块与宅基地重叠', '承包地块与其它自然资源部门要求的要素重叠'].includes(x))) {
    d_p6 = 5.0;
  } else {
    d_p6 = Math.min(form.value.prog_6.length * 0.5, 5.0);
  }

  let d_p7 = 0.0;
  if (form.value.prog_7.some(x => ['档案整理第三方无涉密档案整理资质', '没有进行档案验收', '档案验收不符合相关标准'].includes(x))) {
    d_p7 = 5.0;
  } else {
    d_p7 = Math.min(form.value.prog_7.length * 1.0, 5.0);
  }
  
  let deduct_prog = Math.min(d_p1 + d_p2 + d_p3 + d_p4 + d_p5 + d_p6 + d_p7, 30.0);
  let score_prog = Math.max(30.0 - deduct_prog, 0.0);

  // 3. 政策落实 (满分15)
  let d_pol1 = Math.min(form.value.policy_1.length * 1.0, 3.0);
  let c_2 = (Number(form.value.policy_2_1) || 0) + (Number(form.value.policy_2_2) || 0) + (Number(form.value.policy_2_3) || 0);
  let d_pol2 = Math.min(c_2 * 1.0, 3.0);
  let c_3 = (Number(form.value.policy_3_1) || 0) + (Number(form.value.policy_3_2) || 0) + (Number(form.value.policy_3_3) || 0) + (Number(form.value.policy_3_4) || 0) + (Number(form.value.policy_3_5) || 0);
  let d_pol3 = Math.min(c_3 * 1.0, 3.0);
  let d_pol4 = Math.min(form.value.policy_4.length * 0.5, 3.0);
  let d_pol5 = Math.min(form.value.policy_5.length * 0.5, 3.0);
  
  let deduct_policy = Math.min(d_pol1 + d_pol2 + d_pol3 + d_pol4 + d_pol5, 15.0);
  let score_policy = Math.max(15.0 - deduct_policy, 0.0);

  let total = score_mech + score_prog + score_policy + score_effect;
  return Number(total.toFixed(1));
});

const triggerDownload = (url) => {
  const link = document.createElement('a');
  link.href = encodeURI(decodeURI(url));
  link.setAttribute('download', '');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};


// ── 凭证上传与管理 ─────────────────────────────────────────────
const getEvidenceList = (key) => {
  if (!form.value.evidences) return [];
  return form.value.evidences[key] || [];
};

// 客户端高保真快速压缩，避免大图上传卡顿或网络异常
const compressImageClient = (file) => {
  return new Promise((resolve) => {
    // 非图片或小于 500KB 直接上传
    if (!file.type.startsWith('image/') || file.size < 500 * 1024) {
      return resolve(file);
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const maxDim = 1920;
        let width = img.width;
        let height = img.height;
        if (width > maxDim || height > maxDim) {
          if (width > height) {
            height = Math.round((height * maxDim) / width);
            width = maxDim;
          } else {
            width = Math.round((width * maxDim) / height);
            height = maxDim;
          }
        }
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);
        canvas.toBlob((blob) => {
          if (!blob) {
            resolve(file);
          } else {
            const compressedFile = new File([blob], file.name || 'evidence.jpg', {
              type: 'image/jpeg',
              lastModified: Date.now()
            });
            resolve(compressedFile);
          }
        }, 'image/jpeg', 0.85);
      };
      img.onerror = () => resolve(file);
      img.src = e.target.result;
    };
    reader.onerror = () => resolve(file);
    reader.readAsDataURL(file);
  });
};

const onUploadEvidence = async (file, key) => {
  showLoadingToast({ message: '正在上传凭证...', forbidClick: true, duration: 0 });
  try {
    const rawFile = file.file || file;
    const fileToUpload = await compressImageClient(rawFile);
    
    const formData = new FormData();
    formData.append('file', fileToUpload);
    
    const res = await axios.post('/api/upload_evidence', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000
    });
    
    if (res.data.code === 200) {
      if (!form.value.evidences) form.value.evidences = {};
      if (!Array.isArray(form.value.evidences[key])) form.value.evidences[key] = [];
      form.value.evidences[key].push({
        url: res.data.url,
        name: rawFile.name || '凭证图片'
      });
      form.value.evidences = { ...form.value.evidences };
      closeToast();
      showToast({ type: 'success', message: '凭证上传成功' });
      // 自动保存到数据库
      await silentAutoSave();
    } else {
      closeToast();
      showToast(res.data.message || '上传失败');
    }
  } catch (e) {
    closeToast();
    showToast(e.message && e.message.includes('timeout') ? '上传超时，请重试' : '上传异常，请检查网络');
  }
};

const removeEvidence = async (key, idx) => {
  if (form.value.evidences && form.value.evidences[key]) {
    const removedItem = form.value.evidences[key][idx];
    form.value.evidences[key].splice(idx, 1);
    if (form.value.evidences[key].length === 0) {
      delete form.value.evidences[key];
    }
    form.value.evidences = { ...form.value.evidences };
    showToast({ type: 'success', message: '已删除凭证' });

    // 尝试在服务端同步删除文件
    if (removedItem && removedItem.url) {
      try {
        await axios.post('/api/delete_evidence', { url: removedItem.url });
      } catch (e) {
        console.warn('删除服务端凭证文件提示', e);
      }
    }

    // 立即同步保存表单数据到数据库，避免刷新后凭证复现
    await silentAutoSave();
  }
};

const previewEvidence = (url) => {
  showImagePreview({
    images: [url],
    closeable: true,
    closeOnClickOverlay: true,
    closeOnClickImage: true
  });
};

const onSubmit = async () => {
  if (!selectedAreaCode.value) return;
  saving.value = true;
  showLoadingToast({ message: '正在保存...', forbidClick: true });
  try {
    const res = await axios.post('/api/save_neiye', {
      qsdwdm: selectedAreaCode.value,
      qsdwmc: selectedAreaName.value,
      level: selectedAreaLevel.value,
      form_data: form.value,
      score: totalScore.value
    });
    if (res.data.code === 200) {
      showToast({ type: 'success', message: '已保存！当前得分：' + totalScore.value + '分' });
    } else {
      showToast(res.data.message || '保存失败');
    }
  } catch(e) {
    showToast('网络错误');
  } finally {
    saving.value = false;
    closeToast();
  }
};



const exportingVoucher = ref(false);

const onExportVoucher = async () => {
  if (!selectedAreaCode.value) return;
  exportingVoucher.value = true;
  showLoadingToast({ message: '正在生成凭证记录...', forbidClick: true });
  try {
    // auto save state first
    await axios.post('/api/save_neiye', {
      qsdwdm: selectedAreaCode.value,
      qsdwmc: selectedAreaName.value,
      level: selectedAreaLevel.value,
      form_data: form.value,
      score: totalScore.value
    });
    
    const res = await axios.post('/api/export_neiye_voucher', {
      qsdwdm: selectedAreaCode.value,
      qsdwmc: selectedAreaName.value,
      level: selectedAreaLevel.value,
      form_data: form.value
    });
    
    if (res.data.code === 200 && res.data.url) {
      showToast({ type: 'success', message: '已生成，正在下载...' });
      triggerDownload(res.data.url);
    } else {
      showToast(res.data.message || '生成失败');
    }
  } catch(e) {
    showToast('生成文档请求失败');
  } finally {
    exportingVoucher.value = false;
  }
};

// Signature Logic
const showSignModal = ref(false);
const signRole = ref('');
const canvasRef = ref(null);
const canvasWrapperRef = ref(null);
let ctx = null;
let isDrawing = false;
let hasDrawn = false;
let lastX = 0;
let lastY = 0;

const openSignModal = (role) => {
  signRole.value = role;
  showSignModal.value = true;
};

const onSignModalOpened = () => {
  nextTick(() => {
    const canvas = canvasRef.value;
    const wrapper = canvasWrapperRef.value;
    if (!canvas || !wrapper) return;
    
    const rect = wrapper.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 2;
    
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    
    ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = 3.5;
    ctx.strokeStyle = '#000000';
    
    clearCanvas();
  });
};

const clearCanvas = () => {
  if (!canvasRef.value || !ctx) return;
  const rect = canvasWrapperRef.value.getBoundingClientRect();
  ctx.clearRect(0, 0, rect.width, rect.height);
  hasDrawn = false;
};

const getCanvasPos = (e) => {
  const rect = canvasRef.value.getBoundingClientRect();
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

const handleTouchStart = (e) => { e.preventDefault(); const p = getCanvasPos(e); isDrawing = true; lastX = p.x; lastY = p.y; };
const handleTouchMove = (e) => { e.preventDefault(); if(!isDrawing) return; const p = getCanvasPos(e); ctx.beginPath(); ctx.moveTo(lastX, lastY); ctx.lineTo(p.x, p.y); ctx.stroke(); lastX = p.x; lastY = p.y; hasDrawn = true; };
const handleTouchEnd = (e) => { e.preventDefault(); isDrawing = false; };
const handleMouseDown = (e) => { const p = getCanvasPos(e); isDrawing = true; lastX = p.x; lastY = p.y; };
const handleMouseMove = (e) => { if(!isDrawing) return; const p = getCanvasPos(e); ctx.beginPath(); ctx.moveTo(lastX, lastY); ctx.lineTo(p.x, p.y); ctx.stroke(); lastX = p.x; lastY = p.y; hasDrawn = true; };
const handleMouseUp = () => { isDrawing = false; };

const saveSignature = async () => {
  if (!hasDrawn) {
    showToast('请先手写签名');
    return;
  }
  const dataUrl = canvasRef.value.toDataURL('image/png');
  if (signRole.value === 'jcz') {
    form.value.jcz_sign = dataUrl;
  } else {
    form.value.fhz_sign = dataUrl;
  }
  showSignModal.value = false;
  showToast({ type: 'success', message: '签名已暂存，稍后随表单保存' });
  await silentAutoSave();
};

const onExportFeedbackSummary = async () => {
  if (!selectedAreaCode.value) return;
  if (exportingFeedback.value) return;
  exportingFeedback.value = true;
  showLoadingToast({ message: '正在汇总生成问题反馈记录表...', forbidClick: true });
  try {
    // 先自动保存当前内业核查表单状态
    await axios.post('/api/save_neiye', {
      qsdwdm: selectedAreaCode.value,
      qsdwmc: selectedAreaName.value,
      level: selectedAreaLevel.value,
      form_data: form.value,
      score: totalScore.value
    });

    const res = await axios.post('/api/neiye/export_feedback_summary', {
      qsdwdm: selectedAreaCode.value,
      level: selectedAreaLevel.value,
      township_name: selectedTownshipName.value,
      village_name: selectedVillageName.value,
      qsdwmc: selectedAreaName.value,
      form_data: form.value
    });

    if (res.data.code === 200 && res.data.url) {
      showToast({ type: 'success', message: '问题反馈记录表汇总已生成！' });
      triggerDownload(res.data.url);
    } else {
      showToast(res.data.message || '生成失败');
    }
  } catch (e) {
    console.error('导出问题反馈记录表汇总失败:', e);
    showToast('生成请求失败');
  } finally {
    exportingFeedback.value = false;
    closeToast();
  }
};

const onExportAtt6 = async () => {
  if (!selectedAreaCode.value) return;
  exporting6.value = true;
  showLoadingToast({ message: '正在生成附件6文档...', forbidClick: true });
  try {
    // auto save state first
    await axios.post('/api/save_neiye', {
      qsdwdm: selectedAreaCode.value,
      qsdwmc: selectedAreaName.value,
      level: selectedAreaLevel.value,
      form_data: form.value,
      score: totalScore.value
    });
    
    const res = await axios.post('/api/export_neiye_att6', {
      qsdwdm: selectedAreaCode.value,
      qsdwmc: selectedAreaName.value,
      level: selectedAreaLevel.value,
      township_name: selectedTownshipName.value,
      village_name: selectedVillageName.value,
      form_data: form.value
    });
    
    if (res.data.code === 200 && res.data.url) {
      showToast({ type: 'success', message: '附件6已生成，正在下载...' });
      triggerDownload(res.data.url);
    } else {
      showToast(res.data.message || '生成失败');
    }
  } catch(e) {
    showToast('生成文档请求失败');
  } finally {
    exporting6.value = false;
  }
};

const onExportAtt7 = async () => {
  exporting7.value = true;
  showLoadingToast({ message: '正在汇总生成附件7得分表...', forbidClick: true });
  try {
    // auto save county state if county is active
    if (selectedAreaLevel.value === 'county') {
      await axios.post('/api/save_neiye', {
        qsdwdm: selectedAreaCode.value,
        qsdwmc: selectedAreaName.value,
        level: selectedAreaLevel.value,
        form_data: form.value,
        score: totalScore.value
      });
    }
    
    const res = await axios.get('/api/export_neiye_att7');
    if (res.data.code === 200 && res.data.url) {
      showToast({ type: 'success', message: '附件7已生成，正在下载...' });
      triggerDownload(res.data.url);
    } else {
      showToast(res.data.message || '生成失败');
    }
  } catch(e) {
    showToast('生成得分表失败');
  } finally {
    exporting7.value = false;
  }
};
</script>

<style scoped>
.neiye {
  padding-bottom: 60px;
  background-color: #f7f8fa;
  min-height: 100vh;
}

.action-card {
  margin: 12px 16px 0 16px;
  background: #fff;
  border-radius: 8px;
  padding: 14px 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.score-display {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 12px;
}

.score-label {
  font-size: 15px;
  font-weight: bold;
  color: #323233;
}

.score-val {
  font-size: 24px;
  font-weight: 800;
  color: #1989fa;
}

.score-max {
  font-size: 13px;
  font-weight: normal;
  color: #999;
}

.btn-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.group-tip {
  padding: 6px 16px 10px 16px;
  font-size: 12px;
  color: #969799;
  line-height: 1.4;
}

.stepper-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stepper-unit {
  font-size: 14px;
  color: #646566;
}

.evidence-box {
  background: #f0f7ff;
  border: 1px dashed #adc6ff;
  border-radius: 6px;
  margin: 4px 16px 8px 16px;
  padding: 8px 12px;
}
.evidence-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.evidence-title {
  font-size: 12px;
  color: #1989fa;
  font-weight: 500;
  display: flex;
  align-items: center;
}
.uploader-btns {
  display: flex;
  align-items: center;
}
.evidence-imgs {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 8px;
  padding-top: 4px;
}
.img-thumb {
  position: relative;
  width: 60px;
  height: 60px;
  border-radius: 6px;
  border: 1px solid #d9d9d9;
  box-sizing: border-box;
}
.img-thumb img {
  width: 100%;
  height: 100%;
  border-radius: 6px;
  object-fit: cover;
  cursor: pointer;
  display: block;
}
.img-thumb .del-btn {
  position: absolute;
  top: -7px;
  right: -7px;
  width: 22px;
  height: 22px;
  background: #ee0a24;
  color: #ffffff;
  font-size: 15px;
  font-weight: bold;
  line-height: 20px;
  text-align: center;
  border-radius: 50%;
  cursor: pointer;
  z-index: 30;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  user-select: none;
  touch-action: manipulation;
  pointer-events: auto;
}
.img-thumb .del-btn:active {
  transform: scale(0.9);
  background: #cf0820;
}

</style>