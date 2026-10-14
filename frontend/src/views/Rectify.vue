<template>
  <div class="rectify">
    <van-nav-bar title="自查整改" left-text="返回" left-arrow @click-left="onBack" />
    <div class="page-body">
      <!-- 全县问题反馈记录表汇总 -->
      <van-cell-group inset title="全县问题反馈记录表汇总">
        <div style="padding: 14px 16px;">
          <div style="font-size: 13px; color: #666; margin-bottom: 12px; line-height: 1.5;">
            汇总全县各级（县本级、乡镇级、村级）内业核查与外业实地核查发现的全部问题，按“严重、较重、一般”三等评定归类，自动输出横向《问题反馈记录表汇总》。
          </div>
          <van-button
            round
            block
            type="warning"
            icon="orders-o"
            :loading="exportingSummary"
            @click="onExportCountySummary"
          >导出全县问题反馈记录表汇总 (.doc)</van-button>
        </div>
      </van-cell-group>

      <!-- 按乡镇整改通知与台账 -->
      <van-cell-group inset title="按乡镇整改通知书与销号台账" style="margin-top: 16px;">
        <van-field
          v-model="areaText"
          label="乡镇"
          placeholder="请选择乡镇"
          readonly
          is-link
          @click="showPicker = true"
        />
        <van-field label="台账导出选项" label-width="110px">
          <template #input>
            <van-radio-group v-model="att13Filter" direction="horizontal">
              <van-radio name="all">全部导出</van-radio>
              <van-radio name="non_severe">只导出非严重问题</van-radio>
            </van-radio-group>
          </template>
        </van-field>
        <van-field
          v-model="planDeadline"
          label="计划完成时限"
          placeholder="例如：2024年10月15日（选填）"
          clearable
        />
        <van-field
          v-model="actualFinishDate"
          label="实际完成时间"
          placeholder="例如：2024年10月20日（选填）"
          clearable
        />
      </van-cell-group>

      <div class="export-panel">
        <van-button
          round
          block
          type="primary"
          :loading="exporting12"
          :disabled="!selectedTown"
          @click="onExportAtt12"
        >导出附件12_整改通知书</van-button>

        <van-button
          round
          block
          type="success"
          style="margin-top: 12px;"
          :loading="exporting13"
          :disabled="!selectedTown"
          @click="onExportAtt13"
        >导出附件13_问题整改销号台账</van-button>
      </div>
    </div>

    <van-popup v-model:show="showPicker" round position="bottom">
      <van-picker
        :columns="pickerColumns"
        @cancel="showPicker = false"
        @confirm="onPickerConfirm"
      />
    </van-popup>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { hasPerm } from '../utils/auth'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { showToast, showLoadingToast, closeToast } from 'vant'

const router = useRouter()

const areaText = ref('')
const selectedTown = ref(null) // { code, name }
const att13Filter = ref('all') // 'all' | 'non_severe'
const planDeadline = ref('')
const actualFinishDate = ref('')
const showPicker = ref(false)
const pickerColumns = ref([])

const exporting12 = ref(false)
const exporting13 = ref(false)
const exportingSummary = ref(false)

const triggerDownload = (url) => {
  if (!url) return;
  const encodedUrl = encodeURI(decodeURI(url));
  const link = document.createElement('a');
  link.href = encodedUrl;
  link.setAttribute('download', '');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

const onBack = () => router.back()

const onExportCountySummary = async () => {
  if (exportingSummary.value) return;
  exportingSummary.value = true;
  showLoadingToast({ message: '正在汇总全县问题反馈记录...', forbidClick: true });
  try {
    const res = await axios.get('/api/export_county_issue_feedback_summary');
    if (res.data.code === 200 && res.data.url) {
      triggerDownload(res.data.url);
      showToast({ type: 'success', message: '全县问题反馈记录表汇总已生成！' });
    } else {
      showToast(res.data.message || '导出失败');
    }
  } catch (e) {
    console.error('导出全县问题反馈汇总失败:', e);
    showToast('导出失败');
  } finally {
    exportingSummary.value = false;
    closeToast();
  }
};

const initPickerColumns = async () => {
  try {
    const res = await axios.get('/api/hierarchy')
    if (res.data && res.data.code === 200) {
      const townships = res.data.townships || []
      pickerColumns.value = townships.map(t => ({
        text: t.name,
        value: t.code,
        name: t.name
      }))
    }
  } catch (e) {
    console.error('加载乡镇列表失败', e)
    showToast('加载乡镇列表失败')
  }
}

const onPickerConfirm = ({ selectedOptions }) => {
  showPicker.value = false
  const opt = selectedOptions[0]
  if (!opt) return
  selectedTown.value = { code: opt.value, name: opt.name }
  areaText.value = opt.name
}

const onExportAtt12 = async () => {
  if (!selectedTown.value) return
  exporting12.value = true
  try {
    const res = await axios.get('/api/export_rectify_att12?township_name=' + encodeURIComponent(selectedTown.value.name))
    if (res.data.code === 200 && res.data.url) {
      triggerDownload(res.data.url)
      showToast('导出成功')
    } else {
      showToast('导出失败')
    }
  } catch (e) {
    console.error(e)
    showToast('导出失败')
  } finally {
    exporting12.value = false
  }
}

const onExportAtt13 = async () => {
  if (!selectedTown.value) return
  exporting13.value = true
  showLoadingToast({ message: '生成台账中...', forbidClick: true })
  try {
    const res = await axios.get(
      '/api/export_rectify_att13?township_code=' + encodeURIComponent(selectedTown.value.code) +
      '&township_name=' + encodeURIComponent(selectedTown.value.name) +
      '&filter_type=' + encodeURIComponent(att13Filter.value) +
      '&plan_deadline=' + encodeURIComponent(planDeadline.value || '') +
      '&actual_finish_date=' + encodeURIComponent(actualFinishDate.value || '')
    )
    if (res.data.code === 200 && res.data.url) {
      triggerDownload(res.data.url)
      showToast('导出成功')
    } else {
      showToast('导出失败')
    }
  } catch (e) {
    console.error(e)
    showToast('导出失败')
  } finally {
    closeToast()
    exporting13.value = false
  }
}

onMounted(initPickerColumns)
</script>

<style scoped>
.page-body {
  padding: 16px 0;
}
.export-panel {
  padding: 16px;
}
</style>
