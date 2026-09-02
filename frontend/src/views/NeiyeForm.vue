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
        placeholder="请选择县级或乡镇"
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
        <div class="score-val">{{ totalScore }} <span class="score-max">/ {{ selectedAreaLevel === 'county' ? 15 : 70 }}分</span></div>
      </div>
      <div class="btn-group">
        
        
        
          <van-button size="small" type="primary" round :loading="exportingVoucher" @click="onExportVoucher">
            导出凭证记录
          </van-button>
<!-- Township Exports -->
        <template v-if="selectedAreaLevel === 'township'">
          <van-button v-if="hasPerm('neiye_export_att6')" size="small" type="success" round :loading="exporting6" @click="onExportAtt6">
            导出附件6 检查记录表
          </van-button>
        </template>

        

<!-- County Exports -->
        <template v-if="selectedAreaLevel === 'county'">
          <van-button v-if="hasPerm('neiye_export_att6')" size="small" type="success" round :loading="exporting6" @click="onExportAtt6">
            导出附件6 检查记录表（1/4）
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
        <van-cell-group inset title="1. 延包方案与分工 (2分)" style="margin-top: 10px;">
          <van-checkbox-group v-model="form.mech_1">
            <van-cell title="未制定方案 (扣2分)" clickable @click="toggle('mech_1', '未制定方案')">
              <template #right-icon><van-checkbox name="未制定方案" @click.stop /></template>
            </van-cell>
            <!-- 凭证上传区: 未制定方案 -->
            <div v-if="form.mech_1 && form.mech_1.includes('未制定方案')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '未制定方案')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('未制定方案').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('未制定方案')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('未制定方案', idx)">×</span>
                </div>
              </div>
            </div>
            <van-cell title="直接套用上级方案 (扣2分)" clickable @click="toggle('mech_1', '直接套用上级方案')">
              <template #right-icon><van-checkbox name="直接套用上级方案" @click.stop /></template>
            </van-cell>
            <!-- 凭证上传区: 直接套用上级方案 -->
            <div v-if="form.mech_1 && form.mech_1.includes('直接套用上级方案')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '直接套用上级方案')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('直接套用上级方案').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('直接套用上级方案')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('直接套用上级方案', idx)">×</span>
                </div>
              </div>
            </div>
            <van-cell title="分工不明确 (扣2分)" clickable @click="toggle('mech_1', '分工不明确')">
              <template #right-icon><van-checkbox name="分工不明确" @click.stop /></template>
            </van-cell>
            <!-- 凭证上传区: 分工不明确 -->
            <div v-if="form.mech_1 && form.mech_1.includes('分工不明确')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '分工不明确')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('分工不明确').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('分工不明确')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('分工不明确', idx)">×</span>
                </div>
              </div>
            </div>
            <van-cell title="制定程序不合法 (扣2分)" clickable @click="toggle('mech_1', '制定程序不合法')">
              <template #right-icon><van-checkbox name="制定程序不合法" @click.stop /></template>
            </van-cell>
            <!-- 凭证上传区: 制定程序不合法 -->
            <div v-if="form.mech_1 && form.mech_1.includes('制定程序不合法')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '制定程序不合法')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('制定程序不合法').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('制定程序不合法')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('制定程序不合法', idx)">×</span>
                </div>
              </div>
            </div>
          </van-checkbox-group>
          <div class="group-tip">注：发现任何一项扣2分。</div>
        </van-cell-group>
        
        <van-cell-group inset title="2. 经费保障 (10分)" style="margin-top: 10px;">
          <van-checkbox-group v-model="form.mech_2">
            <van-cell title="支付不规范 (扣4分)" clickable @click="toggle('mech_2', '支付不规范')">
              <template #right-icon><van-checkbox name="支付不规范" @click.stop /></template>
            </van-cell>
            <!-- 凭证上传区: 支付不规范 -->
            <div v-if="form.mech_2 && form.mech_2.includes('支付不规范')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '支付不规范')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('支付不规范').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('支付不规范')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('支付不规范', idx)">×</span>
                </div>
              </div>
            </div>
            <van-cell title="支付不及时 (扣4分)" clickable @click="toggle('mech_2', '支付不及时')">
              <template #right-icon><van-checkbox name="支付不及时" @click.stop /></template>
            </van-cell>
            <!-- 凭证上传区: 支付不及时 -->
            <div v-if="form.mech_2 && form.mech_2.includes('支付不及时')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '支付不及时')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('支付不及时').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('支付不及时')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('支付不及时', idx)">×</span>
                </div>
              </div>
            </div>
            <van-cell title="经费没有县级兜底 (扣2分)" clickable @click="toggle('mech_2', '经费没有县级兜底')">
              <template #right-icon><van-checkbox name="经费没有县级兜底" @click.stop /></template>
            </van-cell>
            <!-- 凭证上传区: 经费没有县级兜底 -->
            <div v-if="form.mech_2 && form.mech_2.includes('经费没有县级兜底')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '经费没有县级兜底')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('经费没有县级兜底').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('经费没有县级兜底')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('经费没有县级兜底', idx)">×</span>
                </div>
              </div>
            </div>
          </van-checkbox-group>
          <div class="group-tip">注：支付不及时扣4分；支付不规范扣4分；政府未明确兜底经费的扣2分。</div>
        </van-cell-group>

        <van-cell-group inset title="3. 宣传 (2分)" style="margin-top: 10px;">
          <van-checkbox-group v-model="form.mech_3">
            <van-cell title="没有宣传材料 (扣2分)" clickable @click="toggle('mech_3', '没有宣传材料')">
              <template #right-icon><van-checkbox name="没有宣传材料" @click.stop /></template>
            </van-cell>
            <!-- 凭证上传区: 没有宣传材料 -->
            <div v-if="form.mech_3 && form.mech_3.includes('没有宣传材料')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '没有宣传材料')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('没有宣传材料').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('没有宣传材料')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('没有宣传材料', idx)">×</span>
                </div>
              </div>
            </div>
          </van-checkbox-group>
          <div class="group-tip">注：没有宣传材料不得分（扣2分）。</div>
        </van-cell-group>

        <van-cell-group inset title="4. 培训 (1分)" style="margin-top: 10px;">
          <van-checkbox-group v-model="form.mech_4">
            <van-cell title="没有培训材料 (扣0.5分)" clickable @click="toggle('mech_4', '没有培训材料')">
              <template #right-icon><van-checkbox name="没有培训材料" @click.stop /></template>
            </van-cell>
            <!-- 凭证上传区: 没有培训材料 -->
            <div v-if="form.mech_4 && form.mech_4.includes('没有培训材料')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '没有培训材料')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('没有培训材料').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('没有培训材料')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('没有培训材料', idx)">×</span>
                </div>
              </div>
            </div>
            <van-cell title="没有分批次培训 (扣0.5分)" clickable @click="toggle('mech_4', '没有分批次培训')">
              <template #right-icon><van-checkbox name="没有分批次培训" @click.stop /></template>
            </van-cell>
            <!-- 凭证上传区: 没有分批次培训 -->
            <div v-if="form.mech_4 && form.mech_4.includes('没有分批次培训')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '没有分批次培训')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('没有分批次培训').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('没有分批次培训')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('没有分批次培训', idx)">×</span>
                </div>
              </div>
            </div>
            <van-cell title="培训材料不齐全 (扣0.5分)" clickable @click="toggle('mech_4', '培训材料不齐全')">
              <template #right-icon><van-checkbox name="培训材料不齐全" @click.stop /></template>
            </van-cell>
            <!-- 凭证上传区: 培训材料不齐全 -->
            <div v-if="form.mech_4 && form.mech_4.includes('培训材料不齐全')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '培训材料不齐全')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('培训材料不齐全').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('培训材料不齐全')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('培训材料不齐全', idx)">×</span>
                </div>
              </div>
            </div>
            <van-cell title="培训未覆盖县乡村组 (扣0.5分)" clickable @click="toggle('mech_4', '培训未覆盖县乡村组')">
              <template #right-icon><van-checkbox name="培训未覆盖县乡村组" @click.stop /></template>
            </van-cell>
            <!-- 凭证上传区: 培训未覆盖县乡村组 -->
            <div v-if="form.mech_4 && form.mech_4.includes('培训未覆盖县乡村组')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '培训未覆盖县乡村组')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('培训未覆盖县乡村组').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('培训未覆盖县乡村组')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('培训未覆盖县乡村组', idx)">×</span>
                </div>
              </div>
            </div>
          </van-checkbox-group>
          <div class="group-tip">注：每发现一项扣0.5分，最多扣1分。</div>
        </van-cell-group>
      </van-tab>

      <!-- Township Tabs: Only visible if NOT county -->
      <template v-if="selectedAreaLevel !== 'county'">
        <!-- Tab 2: 程序规范 (30分) -->
        <van-tab title="程序规范(30分)">
          <van-cell-group inset title="1. 成立机构 (5分)" style="margin-top: 10px;">
            <van-checkbox-group v-model="form.prog_1">
              <van-cell title="未召开会议 (扣5分)" clickable @click="toggle('prog_1', '未召开会议')">
                <template #right-icon><van-checkbox name="未召开会议" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 未召开会议 -->
            <div v-if="form.prog_1 && form.prog_1.includes('未召开会议')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '未召开会议')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('未召开会议').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('未召开会议')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('未召开会议', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="未公示工作组名单 (扣5分)" clickable @click="toggle('prog_1', '未公示工作组名单')">
                <template #right-icon><van-checkbox name="未公示工作组名单" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 未公示工作组名单 -->
            <div v-if="form.prog_1 && form.prog_1.includes('未公示工作组名单')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '未公示工作组名单')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('未公示工作组名单').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('未公示工作组名单')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('未公示工作组名单', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="公示时间不足15天 (扣5分)" clickable @click="toggle('prog_1', '公示时间不足15天')">
                <template #right-icon><van-checkbox name="公示时间不足15天" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 公示时间不足15天 -->
            <div v-if="form.prog_1 && form.prog_1.includes('公示时间不足15天')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '公示时间不足15天')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('公示时间不足15天').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('公示时间不足15天')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('公示时间不足15天', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="参会人数不足法定数量 (扣5分)" clickable @click="toggle('prog_1', '参会人数不足法定数量')">
                <template #right-icon><van-checkbox name="参会人数不足法定数量" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 参会人数不足法定数量 -->
            <div v-if="form.prog_1 && form.prog_1.includes('参会人数不足法定数量')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '参会人数不足法定数量')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('参会人数不足法定数量').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('参会人数不足法定数量')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('参会人数不足法定数量', idx)">×</span>
                </div>
              </div>
            </div>
            </van-checkbox-group>
            <div class="group-tip">注：发现任何一项扣5分。</div>
          </van-cell-group>

          <van-cell-group inset title="2. 摸底核实 (5分)" style="margin-top: 10px;">
            <van-checkbox-group v-model="form.prog_2">
              <van-cell title="没有进行摸底" clickable @click="toggle('prog_2', '没有进行摸底')">
                <template #right-icon><van-checkbox name="没有进行摸底" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 没有进行摸底 -->
            <div v-if="form.prog_2 && form.prog_2.includes('没有进行摸底')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '没有进行摸底')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('没有进行摸底').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('没有进行摸底')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('没有进行摸底', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="摸底表农户未签署" clickable @click="toggle('prog_2', '摸底表农户未签署')">
                <template #right-icon><van-checkbox name="摸底表农户未签署" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 摸底表农户未签署 -->
            <div v-if="form.prog_2 && form.prog_2.includes('摸底表农户未签署')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '摸底表农户未签署')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('摸底表农户未签署').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('摸底表农户未签署')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('摸底表农户未签署', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="摸底表中没有表达延包意愿" clickable @click="toggle('prog_2', '摸底表中没有表达延包意愿')">
                <template #right-icon><van-checkbox name="摸底表中没有表达延包意愿" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 摸底表中没有表达延包意愿 -->
            <div v-if="form.prog_2 && form.prog_2.includes('摸底表中没有表达延包意愿')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '摸底表中没有表达延包意愿')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('摸底表中没有表达延包意愿').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('摸底表中没有表达延包意愿')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('摸底表中没有表达延包意愿', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="摸底表其它签署不齐全" clickable @click="toggle('prog_2', '摸底表其它签署不齐全')">
                <template #right-icon><van-checkbox name="摸底表其它签署不齐全" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 摸底表其它签署不齐全 -->
            <div v-if="form.prog_2 && form.prog_2.includes('摸底表其它签署不齐全')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '摸底表其它签署不齐全')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('摸底表其它签署不齐全').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('摸底表其它签署不齐全')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('摸底表其它签署不齐全', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="特殊人员摸底不清或未统计" clickable @click="toggle('prog_2', '特殊人员摸底不清或未统计')">
                <template #right-icon><van-checkbox name="特殊人员摸底不清或未统计" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 特殊人员摸底不清或未统计 -->
            <div v-if="form.prog_2 && form.prog_2.includes('特殊人员摸底不清或未统计')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '特殊人员摸底不清或未统计')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('特殊人员摸底不清或未统计').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('特殊人员摸底不清或未统计')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('特殊人员摸底不清或未统计', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="户变化未统计" clickable @click="toggle('prog_2', '户变化未统计')">
                <template #right-icon><van-checkbox name="户变化未统计" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 户变化未统计 -->
            <div v-if="form.prog_2 && form.prog_2.includes('户变化未统计')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '户变化未统计')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('户变化未统计').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('户变化未统计')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('户变化未统计', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="矛盾纠纷未登记或处理不当" clickable @click="toggle('prog_2', '矛盾纠纷未登记或处理不当')">
                <template #right-icon><van-checkbox name="矛盾纠纷未登记或处理不当" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 矛盾纠纷未登记或处理不当 -->
            <div v-if="form.prog_2 && form.prog_2.includes('矛盾纠纷未登记或处理不当')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '矛盾纠纷未登记或处理不当')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('矛盾纠纷未登记或处理不当').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('矛盾纠纷未登记或处理不当')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('矛盾纠纷未登记或处理不当', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="承包地变化未摸清" clickable @click="toggle('prog_2', '承包地变化未摸清')">
                <template #right-icon><van-checkbox name="承包地变化未摸清" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 承包地变化未摸清 -->
            <div v-if="form.prog_2 && form.prog_2.includes('承包地变化未摸清')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '承包地变化未摸清')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('承包地变化未摸清').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('承包地变化未摸清')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('承包地变化未摸清', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="没有应确尽确" clickable @click="toggle('prog_2', '没有应确尽确')">
                <template #right-icon><van-checkbox name="没有应确尽确" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 没有应确尽确 -->
            <div v-if="form.prog_2 && form.prog_2.includes('没有应确尽确')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '没有应确尽确')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('没有应确尽确').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('没有应确尽确')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('没有应确尽确', idx)">×</span>
                </div>
              </div>
            </div>
            </van-checkbox-group>
            <div class="group-tip">注：每发现一项扣0.5分，扣完5分为止。</div>
          </van-cell-group>

          <van-cell-group inset title="3. 制定方案 (5分)" style="margin-top: 10px;">
            <van-checkbox-group v-model="form.prog_3">
              <van-cell title="没有延包方案 (扣5分)" clickable @click="toggle('prog_3', '没有延包方案')">
                <template #right-icon><van-checkbox name="没有延包方案" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 没有延包方案 -->
            <div v-if="form.prog_3 && form.prog_3.includes('没有延包方案')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '没有延包方案')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('没有延包方案').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('没有延包方案')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('没有延包方案', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="延包方案未上报 (扣5分)" clickable @click="toggle('prog_3', '延包方案未上报')">
                <template #right-icon><van-checkbox name="延包方案未上报" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 延包方案未上报 -->
            <div v-if="form.prog_3 && form.prog_3.includes('延包方案未上报')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '延包方案未上报')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('延包方案未上报').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('延包方案未上报')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('延包方案未上报', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="延包方案未公示 (扣5分)" clickable @click="toggle('prog_3', '延包方案未公示')">
                <template #right-icon><van-checkbox name="延包方案未公示" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 延包方案未公示 -->
            <div v-if="form.prog_3 && form.prog_3.includes('延包方案未公示')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '延包方案未公示')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('延包方案未公示').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('延包方案未公示')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('延包方案未公示', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="未召开会议讨论延包方案 (扣5分)" clickable @click="toggle('prog_3', '未召开会议讨论延包方案')">
                <template #right-icon><van-checkbox name="未召开会议讨论延包方案" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 未召开会议讨论延包方案 -->
            <div v-if="form.prog_3 && form.prog_3.includes('未召开会议讨论延包方案')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '未召开会议讨论延包方案')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('未召开会议讨论延包方案').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('未召开会议讨论延包方案')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('未召开会议讨论延包方案', idx)">×</span>
                </div>
              </div>
            </div>
            </van-checkbox-group>
            <div class="group-tip">注：发现任意一项扣5分。</div>
          </van-cell-group>

          <van-cell-group inset title="4. 调查公示 (2分)" style="margin-top: 10px;">
            <van-checkbox-group v-model="form.prog_4">
              <van-cell title="没有公示材料 (直接扣2分)" clickable @click="toggle('prog_4', '没有公示材料')">
                <template #right-icon><van-checkbox name="没有公示材料" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 没有公示材料 -->
            <div v-if="form.prog_4 && form.prog_4.includes('没有公示材料')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '没有公示材料')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('没有公示材料').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('没有公示材料')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('没有公示材料', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="没有公示或不足15天 (直接扣2分)" clickable @click="toggle('prog_4', '没有公示或不足15天')">
                <template #right-icon><van-checkbox name="没有公示或不足15天" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 没有公示或不足15天 -->
            <div v-if="form.prog_4 && form.prog_4.includes('没有公示或不足15天')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '没有公示或不足15天')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('没有公示或不足15天').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('没有公示或不足15天')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('没有公示或不足15天', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="公示结果未确认" clickable @click="toggle('prog_4', '公示结果未确认')">
                <template #right-icon><van-checkbox name="公示结果未确认" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 公示结果未确认 -->
            <div v-if="form.prog_4 && form.prog_4.includes('公示结果未确认')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '公示结果未确认')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('公示结果未确认').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('公示结果未确认')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('公示结果未确认', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="各类资料不齐全" clickable @click="toggle('prog_4', '各类资料不齐全')">
                <template #right-icon><van-checkbox name="各类资料不齐全" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 各类资料不齐全 -->
            <div v-if="form.prog_4 && form.prog_4.includes('各类资料不齐全')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '各类资料不齐全')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('各类资料不齐全').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('各类资料不齐全')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('各类资料不齐全', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="各类资料制作粗糙" clickable @click="toggle('prog_4', '各类资料制作粗糙')">
                <template #right-icon><van-checkbox name="各类资料制作粗糙" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 各类资料制作粗糙 -->
            <div v-if="form.prog_4 && form.prog_4.includes('各类资料制作粗糙')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '各类资料制作粗糙')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('各类资料制作粗糙').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('各类资料制作粗糙')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('各类资料制作粗糙', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="各类资料签署不规范" clickable @click="toggle('prog_4', '各类资料签署不规范')">
                <template #right-icon><van-checkbox name="各类资料签署不规范" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 各类资料签署不规范 -->
            <div v-if="form.prog_4 && form.prog_4.includes('各类资料签署不规范')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '各类资料签署不规范')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('各类资料签署不规范').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('各类资料签署不规范')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('各类资料签署不规范', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="权属证明材料不齐全" clickable @click="toggle('prog_4', '权属证明材料不齐全')">
                <template #right-icon><van-checkbox name="权属证明材料不齐全" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 权属证明材料不齐全 -->
            <div v-if="form.prog_4 && form.prog_4.includes('权属证明材料不齐全')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '权属证明材料不齐全')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('权属证明材料不齐全').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('权属证明材料不齐全')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('权属证明材料不齐全', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="其它证明材料不齐全" clickable @click="toggle('prog_4', '其它证明材料不齐全')">
                <template #right-icon><van-checkbox name="其它证明材料不齐全" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 其它证明材料不齐全 -->
            <div v-if="form.prog_4 && form.prog_4.includes('其它证明材料不齐全')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '其它证明材料不齐全')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('其它证明材料不齐全').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('其它证明材料不齐全')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('其它证明材料不齐全', idx)">×</span>
                </div>
              </div>
            </div>
            </van-checkbox-group>
            <div class="group-tip">注：公示不足15天或无公示材料扣2分；发现其它任意一项扣0.5分，扣完2分为止。</div>
          </van-cell-group>

          <van-cell-group inset title="5. 签订合同 (3分)" style="margin-top: 10px;">
            <van-checkbox-group v-model="form.prog_5">
              <van-cell title="合同版本格式不正确 (扣3分)" clickable @click="toggle('prog_5', '合同版本格式不正确')">
                <template #right-icon><van-checkbox name="合同版本格式不正确" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 合同版本格式不正确 -->
            <div v-if="form.prog_5 && form.prog_5.includes('合同版本格式不正确')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '合同版本格式不正确')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('合同版本格式不正确').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('合同版本格式不正确')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('合同版本格式不正确', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="合同网签率未达到95% (扣3分)" clickable @click="toggle('prog_5', '合同网签率未达到95%')">
                <template #right-icon><van-checkbox name="合同网签率未达到95%" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 合同网签率未达到95% -->
            <div v-if="form.prog_5 && form.prog_5.includes('合同网签率未达到95%')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '合同网签率未达到95%')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('合同网签率未达到95%').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('合同网签率未达到95%')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('合同网签率未达到95%', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="没有地块示意图 (扣3分)" clickable @click="toggle('prog_5', '没有地块示意图')">
                <template #right-icon><van-checkbox name="没有地块示意图" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 没有地块示意图 -->
            <div v-if="form.prog_5 && form.prog_5.includes('没有地块示意图')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '没有地块示意图')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('没有地块示意图').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('没有地块示意图')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('没有地块示意图', idx)">×</span>
                </div>
              </div>
            </div>
            </van-checkbox-group>
            <div class="group-tip">注：发现任意一项扣3分。</div>
          </van-cell-group>

          <van-cell-group inset title="6. 完善证书 (5分)" style="margin-top: 10px;">
            <van-checkbox-group v-model="form.prog_6">
              <van-cell title="未进行信息共享 (扣5分)" clickable @click="toggle('prog_6', '未进行信息共享')">
                <template #right-icon><van-checkbox name="未进行信息共享" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 未进行信息共享 -->
            <div v-if="form.prog_6 && form.prog_6.includes('未进行信息共享')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '未进行信息共享')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('未进行信息共享').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('未进行信息共享')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('未进行信息共享', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="未与不动产登记部门有序衔接 (扣5分)" clickable @click="toggle('prog_6', '未与不动产登记部门有序衔接')">
                <template #right-icon><van-checkbox name="未与不动产登记部门有序衔接" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 未与不动产登记部门有序衔接 -->
            <div v-if="form.prog_6 && form.prog_6.includes('未与不动产登记部门有序衔接')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '未与不动产登记部门有序衔接')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('未与不动产登记部门有序衔接').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('未与不动产登记部门有序衔接')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('未与不动产登记部门有序衔接', idx)">×</span>
                </div>
              </div>
            </div>
            </van-checkbox-group>
            <div class="group-tip">注：发现任意一项扣5分。</div>
          </van-cell-group>
          
          <van-cell-group inset title="7. 资料归档 (5分)" style="margin-top: 10px;">
            <van-checkbox-group v-model="form.prog_7">
              <van-cell title="档案整理第三方无涉密档案整理资质 (扣5分)" clickable @click="toggle('prog_7', '档案整理第三方无涉密档案整理资质')">
                <template #right-icon><van-checkbox name="档案整理第三方无涉密档案整理资质" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 档案整理第三方无涉密档案整理资质 -->
            <div v-if="form.prog_7 && form.prog_7.includes('档案整理第三方无涉密档案整理资质')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '档案整理第三方无涉密档案整理资质')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('档案整理第三方无涉密档案整理资质').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('档案整理第三方无涉密档案整理资质')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('档案整理第三方无涉密档案整理资质', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="没有进行档案验收 (扣5分)" clickable @click="toggle('prog_7', '没有进行档案验收')">
                <template #right-icon><van-checkbox name="没有进行档案验收" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 没有进行档案验收 -->
            <div v-if="form.prog_7 && form.prog_7.includes('没有进行档案验收')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '没有进行档案验收')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('没有进行档案验收').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('没有进行档案验收')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('没有进行档案验收', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="档案验收不符合相关标准 (扣5分)" clickable @click="toggle('prog_7', '档案验收不符合相关标准')">
                <template #right-icon><van-checkbox name="档案验收不符合相关标准" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 档案验收不符合相关标准 -->
            <div v-if="form.prog_7 && form.prog_7.includes('档案验收不符合相关标准')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '档案验收不符合相关标准')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('档案验收不符合相关标准').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('档案验收不符合相关标准')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('档案验收不符合相关标准', idx)">×</span>
                </div>
              </div>
            </div>
            </van-checkbox-group>
            <div class="group-tip">注：发现任意一项扣5分。</div>
          </van-cell-group>
        </van-tab>

        <!-- Tab 3: 政策落实 (15分) -->
        <van-tab title="政策落实(15分)">
          <van-cell-group inset title="1. 大稳定、小调整 (3分)" style="margin-top: 10px;">
            <van-checkbox-group v-model="form.policy_1">
              <van-cell title="小调整比率过大或手续不齐全 (扣1分)" clickable @click="toggle('policy_1', '小调整比率过大或手续不齐全')">
                <template #right-icon><van-checkbox name="小调整比率过大或手续不齐全" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 小调整比率过大或手续不齐全 -->
            <div v-if="form.policy_1 && form.policy_1.includes('小调整比率过大或手续不齐全')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '小调整比率过大或手续不齐全')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('小调整比率过大或手续不齐全').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('小调整比率过大或手续不齐全')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('小调整比率过大或手续不齐全', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="打乱重分 (扣1分)" clickable @click="toggle('policy_1', '打乱重分')">
                <template #right-icon><van-checkbox name="打乱重分" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 打乱重分 -->
            <div v-if="form.policy_1 && form.policy_1.includes('打乱重分')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '打乱重分')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('打乱重分').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('打乱重分')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('打乱重分', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="违法调整或收回承包地 (扣1分)" clickable @click="toggle('policy_1', '违法调整或收回承包地')">
                <template #right-icon><van-checkbox name="违法调整或收回承包地" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 违法调整或收回承包地 -->
            <div v-if="form.policy_1 && form.policy_1.includes('违法调整或收回承包地')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '违法调整或收回承包地')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('违法调整或收回承包地').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('违法调整或收回承包地')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('违法调整或收回承包地', idx)">×</span>
                </div>
              </div>
            </div>
            </van-checkbox-group>
            <div class="group-tip">注：发现任何一项扣1分，扣完3分为止。</div>
          </van-cell-group>

          <van-cell-group inset title="2. 保障土地承包权益 (3分)" style="margin-top: 10px;">
            <van-field name="policy_2_1" label="未保障特殊群体权益">
              <template #input>
                <div class="stepper-wrap">
                  <van-stepper v-model="form.policy_2_1" min="0" step="1" @change="(val) => onStepperChange('policy_2_1', '未保障特殊群体权益', val)" />
                  <span class="stepper-unit">起</span>
                </div>
              </template>
            </van-field>
            <div v-if="form.policy_2_1 > 0" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '未保障特殊群体权益')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('未保障特殊群体权益').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('未保障特殊群体权益')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('未保障特殊群体权益', idx)">×</span>
                </div>
              </div>
            </div>
            <van-field name="policy_2_2" label="未保障无地户权益">
              <template #input>
                <div class="stepper-wrap">
                  <van-stepper v-model="form.policy_2_2" min="0" step="1" @change="(val) => onStepperChange('policy_2_2', '未保障无地农户权益', val)" />
                  <span class="stepper-unit">起</span>
                </div>
              </template>
            </van-field>
            <div v-if="form.policy_2_2 > 0" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '未保障无地农户权益')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('未保障无地农户权益').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('未保障无地农户权益')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('未保障无地农户权益', idx)">×</span>
                </div>
              </div>
            </div>
            <div class="group-tip">注：发现一起扣1分，扣完3分为止。</div>
          </van-cell-group>
          
          <van-cell-group inset title="3. 依法收回消亡户承包地 (3分)" style="margin-top: 10px;">
            <van-field name="policy_3_1" label="没有应收尽收">
              <template #input>
                <div class="stepper-wrap">
                  <van-stepper v-model="form.policy_3_1" min="0" step="1" @change="(val) => onStepperChange('policy_3_1', '没有应收尽收', val)" />
                  <span class="stepper-unit">起</span>
                </div>
              </template>
            </van-field>
            <div v-if="form.policy_3_1 > 0" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '没有应收尽收')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('没有应收尽收').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('没有应收尽收')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('没有应收尽收', idx)">×</span>
                </div>
              </div>
            </div>
            <van-field name="policy_3_2" label="采用不正当方式隐匿消亡户">
              <template #input>
                <div class="stepper-wrap">
                  <van-stepper v-model="form.policy_3_2" min="0" step="1" @change="(val) => onStepperChange('policy_3_2', '收回程序形式不符合法律规定', val)" />
                  <span class="stepper-unit">起</span>
                </div>
              </template>
            </van-field>
            <div v-if="form.policy_3_2 > 0" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '不正当方式隐匿消亡户')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('不正当方式隐匿消亡户').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('不正当方式隐匿消亡户')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('不正当方式隐匿消亡户', idx)">×</span>
                </div>
              </div>
            </div>
            <div class="group-tip">注：发现一起扣1分，扣完3分为止。</div>
          </van-cell-group>
          
          <van-cell-group inset title="4. 严格机动地和新增耕地管理 (3分)" style="margin-top: 10px;">
            <van-checkbox-group v-model="form.policy_4">
              <van-cell title="机动地、新增耕地处置不当 (扣0.5分)" clickable @click="toggle('policy_4', '机动地、新增耕地处置不当')">
                <template #right-icon><van-checkbox name="机动地、新增耕地处置不当" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 机动地、新增耕地处置不当 -->
            <div v-if="form.policy_4 && form.policy_4.includes('机动地、新增耕地处置不当')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '机动地、新增耕地处置不当')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('机动地、新增耕地处置不当').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('机动地、新增耕地处置不当')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('机动地、新增耕地处置不当', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="机动地比率过高 (扣0.5分)" clickable @click="toggle('policy_4', '机动地比率过高')">
                <template #right-icon><van-checkbox name="机动地比率过高" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 机动地比率过高 -->
            <div v-if="form.policy_4 && form.policy_4.includes('机动地比率过高')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '机动地比率过高')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('机动地比率过高').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('机动地比率过高')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('机动地比率过高', idx)">×</span>
                </div>
              </div>
            </div>
            </van-checkbox-group>
            <div class="group-tip">注：发现一项扣0.5分，扣完3分为止。</div>
          </van-cell-group>
          
          <van-cell-group inset title="5. 从严掌握确权确股不确地 (3分)" style="margin-top: 10px;">
            <van-checkbox-group v-model="form.policy_5">
              <van-cell title="违背农户意愿强行推进 (扣0.5分)" clickable @click="toggle('policy_5', '违背农户意愿强行推进')">
                <template #right-icon><van-checkbox name="违背农户意愿强行推进" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 违背农户意愿强行推进 -->
            <div v-if="form.policy_5 && form.policy_5.includes('违背农户意愿强行推进')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '违背农户意愿强行推进')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('违背农户意愿强行推进').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('违背农户意愿强行推进')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('违背农户意愿强行推进', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="确权确股不确地手续不齐全 (扣0.5分)" clickable @click="toggle('policy_5', '确权确股不确地手续不齐全')">
                <template #right-icon><van-checkbox name="确权确股不确地手续不齐全" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 确权确股不确地手续不齐全 -->
            <div v-if="form.policy_5 && form.policy_5.includes('确权确股不确地手续不齐全')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '确权确股不确地手续不齐全')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('确权确股不确地手续不齐全').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('确权确股不确地手续不齐全')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('确权确股不确地手续不齐全', idx)">×</span>
                </div>
              </div>
            </div>
            </van-checkbox-group>
            <div class="group-tip">注：发现一项扣0.5分，扣完3分为止。</div>
          </van-cell-group>
        </van-tab>

        <!-- Tab 4: 工作成效 (10分) -->
        <van-tab title="工作成效(10分)">
          <van-cell-group inset title="加强风险防范 (10分)" style="margin-top: 10px;">
            <van-checkbox-group v-model="form.effect_1">
              <van-cell title="未建立矛盾纠纷处置机制 (扣1分)" clickable @click="toggle('effect_1', '未建立矛盾纠纷处置机制')">
                <template #right-icon><van-checkbox name="未建立矛盾纠纷处置机制" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 未建立矛盾纠纷处置机制 -->
            <div v-if="form.effect_1 && form.effect_1.includes('未建立矛盾纠纷处置机制')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '未建立矛盾纠纷处置机制')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('未建立矛盾纠纷处置机制').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('未建立矛盾纠纷处置机制')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('未建立矛盾纠纷处置机制', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="未建立舆情处置办法 (扣1分)" clickable @click="toggle('effect_1', '未建立舆情处置办法')">
                <template #right-icon><van-checkbox name="未建立舆情处置办法" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 未建立舆情处置办法 -->
            <div v-if="form.effect_1 && form.effect_1.includes('未建立舆情处置办法')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '未建立舆情处置办法')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('未建立舆情处置办法').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('未建立舆情处置办法')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('未建立舆情处置办法', idx)">×</span>
                </div>
              </div>
            </div>
              <van-cell title="没有矛盾纠纷处理台账 (扣1分)" clickable @click="toggle('effect_1', '没有矛盾纠纷处理台账')">
                <template #right-icon><van-checkbox name="没有矛盾纠纷处理台账" @click.stop /></template>
              </van-cell>
            <!-- 凭证上传区: 没有矛盾纠纷处理台账 -->
            <div v-if="form.effect_1 && form.effect_1.includes('没有矛盾纠纷处理台账')" class="evidence-box">
              <div class="evidence-header">
                <span class="evidence-title"><van-icon name="photograph" color="#1989fa" /> 扣分凭证：</span>
                <div class="uploader-btns">
                  <van-uploader :after-read="(f) => onUploadEvidence(f, '没有矛盾纠纷处理台账')" accept="image/*">
                    <van-button size="mini" icon="photograph" plain type="primary">拍照/上传</van-button>
                  </van-uploader>
                </div>
              </div>
              <div v-if="getEvidenceList('没有矛盾纠纷处理台账').length > 0" class="evidence-imgs">
                <div v-for="(img, idx) in getEvidenceList('没有矛盾纠纷处理台账')" :key="idx" class="img-thumb">
                  <img :src="img.url" @click="previewEvidence(img.url)" />
                  <span class="del-btn" @click.stop.prevent="removeEvidence('没有矛盾纠纷处理台账', idx)">×</span>
                </div>
              </div>
            </div>
            </van-checkbox-group>
            <div class="group-tip">注：发现任何一项扣1分。</div>
          </van-cell-group>
        </van-tab>
      </template>
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

const saving = ref(false);
const exporting6 = ref(false);
const exporting7 = ref(false);

const pickerColumns = ref([]);

const form = ref({
  mech_1: [], mech_2: [], mech_3: [], mech_4: [],
  prog_1: [], prog_2: [], prog_3: [], prog_4: [], prog_5: [], prog_6: [], prog_7: [],
  policy_1: [], policy_2_1: 0, policy_2_2: 0, policy_3_1: 0, policy_3_2: 0, policy_4: [], policy_5: [],
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
    const res = await axios.get('/api/hierarchy');
    if (res.data.code === 200) {
      const townships = res.data.townships || [];
      const county = res.data.county;
      
      pickerColumns.value = [];
      if (county) {
        pickerColumns.value.push({ text: `${county.name} (县级)`, value: county.code, level: 'county' });
      }
      pickerColumns.value.push(
        ...townships.map(t => ({
          text: t.name,
          value: t.code,
          level: 'township'
        }))
      );
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
  
  if (selectedAreaLevel.value === 'county') {
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
        policy_3_1: fd.policy_3_1 || 0,
        policy_3_2: fd.policy_3_2 || 0,
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
        policy_1: [], policy_2_1: 0, policy_2_2: 0, policy_3_1: 0, policy_3_2: 0, policy_4: [], policy_5: [],
        effect_1: [], jcz_name: '', fhz_name: ''
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

  if (selectedAreaLevel.value === 'county') {
    return Number(score_mech.toFixed(1));
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
  let d_p6 = form.value.prog_6.length > 0 ? 5.0 : 0.0;
  let d_p7 = form.value.prog_7.length > 0 ? 5.0 : 0.0;
  
  let deduct_prog = Math.min(d_p1 + d_p2 + d_p3 + d_p4 + d_p5 + d_p6 + d_p7, 30.0);
  let score_prog = Math.max(30.0 - deduct_prog, 0.0);

  // 3. 政策落实 (满分15)
  let d_pol1 = Math.min(form.value.policy_1.length * 1.0, 3.0);
  let d_pol2 = Math.min(((Number(form.value.policy_2_1) || 0) + (Number(form.value.policy_2_2) || 0)) * 1.0, 3.0);
  let d_pol3 = Math.min(((Number(form.value.policy_3_1) || 0) + (Number(form.value.policy_3_2) || 0)) * 1.0, 3.0);
  let d_pol4 = Math.min(form.value.policy_4.length * 0.5, 3.0);
  let d_pol5 = Math.min(form.value.policy_5.length * 0.5, 3.0);
  
  let deduct_policy = Math.min(d_pol1 + d_pol2 + d_pol3 + d_pol4 + d_pol5, 15.0);
  let score_policy = Math.max(15.0 - deduct_policy, 0.0);

  // 4. 工作成效 (满分10)
  let deduct_effect = Math.min(form.value.effect_1.length * 1.0, 10.0);
  let score_effect = Math.max(10.0 - deduct_effect, 0.0);

  let total = score_mech + score_prog + score_policy + score_effect;
  return Number(total.toFixed(1));
});

const triggerDownload = (url) => {
  const link = document.createElement('a');
  link.href = url;
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
    if (selectedAreaCode.value === '341124') {
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