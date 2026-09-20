<template>
  <div class="batch-export">
    <van-nav-bar title="附件导出" left-text="返回" left-arrow @click-left="onBack" />
    <div class="page-body">
      <van-cell-group inset title="选择导出层级与范围">
        <van-field
          v-model="levelText"
          label="导出层级"
          placeholder="请选择层级"
          readonly
          is-link
          @click="showLevelPicker = true"
        />
        <van-field
          v-if="selectedLevel === 'township'"
          v-model="areaText"
          label="选择乡镇"
          placeholder="请选择乡镇"
          readonly
          is-link
          @click="showTownPicker = true"
        />
      </van-cell-group>

      <van-cell-group inset title="选择要导出的附件" v-if="selectedLevel" style="margin-top: 16px;">
        <van-checkbox-group v-model="selectedAttachments">
          <van-cell-group>
            <van-cell
              v-for="item in availableAttachments"
              :key="item.id"
              clickable
              :title="item.name"
              @click="toggleAttachment(item.id)"
            >
              <template #right-icon>
                <van-checkbox :name="item.id" @click.stop />
              </template>
            </van-cell>
          </van-cell-group>
        </van-checkbox-group>
      </van-cell-group>

      <div class="export-panel">
        <van-button
          round
          block
          type="primary"
          :loading="exporting"
          :disabled="!canExport"
          @click="onBatchExport"
        >打包生成并下载</van-button>
        <div class="dir-tip" v-if="selectedLevel">
          系统将自动生成所需的附件并打包为 ZIP 文件下载至系统默认下载位置。
        </div>
      </div>
    </div>

    <!-- 层级选择 -->
    <van-popup v-model:show="showLevelPicker" round position="bottom">
      <van-picker
        :columns="levelColumns"
        @cancel="showLevelPicker = false"
        @confirm="onLevelConfirm"
      />
    </van-popup>

    <!-- 乡镇选择 -->
    <van-popup v-model:show="showTownPicker" round position="bottom">
      <van-picker
        :columns="townColumns"
        @cancel="showTownPicker = false"
        @confirm="onTownConfirm"
      />
    </van-popup>

    <!-- 打包进度看板弹窗 -->
    <van-dialog
      v-model:show="showProgressDialog"
      title="批量打包生成进度"
      :show-confirm-button="taskCompleted || taskFailed"
      :confirm-button-text="taskFailed ? '重试或关闭' : '完成'"
      :close-on-click-overlay="false"
      class="export-dialog"
    >
      <div class="progress-box">
        <div class="progress-circle-wrap">
          <van-circle
            v-model:current-rate="taskPercent"
            :rate="targetPercent"
            :speed="100"
            :color="taskFailed ? '#ee0a24' : '#1989fa'"
            :text="taskPercent + '%'"
            size="110px"
            stroke-width="60"
          />
        </div>
        <div class="progress-info">
          <div class="status-title" :class="{ 'error-text': taskFailed }">
            {{ taskFailed ? '打包生成中断' : (taskCompleted ? '打包已完成，正在下载' : '正在全力生成中...') }}
          </div>
          <div class="current-step-msg">{{ taskMessage }}</div>
        </div>
        <div class="progress-tip" v-if="!taskCompleted && !taskFailed">
          <van-loading size="14px" type="spinner" style="display: inline-block; margin-right: 6px;" />
          Word COM 跨进程正在排版与渲染表格，请保持页面打开
        </div>
      </div>
    </van-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { showToast } from 'vant'

const router = useRouter()

const levelText = ref('')
const selectedLevel = ref(null) // 'county' | 'township'
const showLevelPicker = ref(false)
const levelColumns = [
  { text: '全县（县级总附件）', value: 'county' },
  { text: '各乡镇（乡镇级所有附件）', value: 'township' }
]

const areaText = ref('')
const selectedTown = ref(null) // { code, name }
const showTownPicker = ref(false)
const townColumns = ref([])

const exporting = ref(false)
const selectedAttachments = ref([])

// 进度弹窗相关状态
const showProgressDialog = ref(false)
const taskPercent = ref(0)
const targetPercent = ref(0)
const taskMessage = ref('准备启动中...')
const taskCompleted = ref(false)
const taskFailed = ref(false)
let pollTimer = null

const countyAttachments = [
  { id: 'att5', name: '附件5：自查抽样统计表（全县汇总）' },
  { id: 'village_sample_stats', name: '各行政村抽样比例统计表（.xlsx）' },
  { id: 'att6_county', name: '附件6：县级自查内业组检查记录表' },
  { id: 'att7', name: '附件7：县级自查内业组检查得分表' },
  { id: 'att9', name: '附件9：县级自查外业组检查得分表' },
  { id: 'att10', name: '附件10：县级自查得分汇总表' },
  { id: 'att11', name: '附件11：县级自查验收评定表' }
]

const townshipAttachments = [
  { id: 'att4', name: '附件4：成果检查验收申请表' },
  { id: 'att5', name: '附件5：自查抽样统计表' },
  { id: 'sample_detail_excel', name: '各乡镇自查抽样明细表（.xlsx）' },
  { id: 'att6_township', name: '附件6：县级自查内业组检查记录表' },
  { id: 'att8', name: '附件8：外业核查记录表' },
  { id: 'inquiry', name: '附件：询问笔录（该镇所有已填报农户）' },
  { id: 'village_meeting_photos', name: '导出现场会照片（各村现场会照片.docx）' },
  { id: 'att12', name: '附件12：整改通知书' },
  { id: 'att13', name: '附件13：问题整改销号台账' }
]

const availableAttachments = computed(() => {
  if (selectedLevel.value === 'county') return countyAttachments
  if (selectedLevel.value === 'township') return townshipAttachments
  return []
})

const toggleAttachment = (id) => {
  const index = selectedAttachments.value.indexOf(id)
  if (index > -1) {
    selectedAttachments.value.splice(index, 1)
  } else {
    selectedAttachments.value.push(id)
  }
}

const onBack = () => router.back()

const initTowns = async () => {
  try {
    const res = await axios.get('/api/hierarchy')
    if (res.data && res.data.code === 200) {
      const townships = res.data.townships || []
      townColumns.value = []
      townColumns.value.push(
        ...townships.map(t => ({
          text: t.name,
          value: t.code,
          name: t.name
        }))
      )
    }
  } catch (e) {
    console.error('加载乡镇列表失败', e)
  }
}

const onLevelConfirm = ({ selectedOptions }) => {
  showLevelPicker.value = false
  const opt = selectedOptions[0]
  if (!opt) return
  selectedLevel.value = opt.value
  levelText.value = opt.text
  if (opt.value === 'county') {
    selectedTown.value = null
    areaText.value = ''
    selectedAttachments.value = countyAttachments.map(a => a.id)
  } else {
    selectedAttachments.value = townshipAttachments.map(a => a.id)
  }
}

const onTownConfirm = ({ selectedOptions }) => {
  showTownPicker.value = false
  const opt = selectedOptions[0]
  if (!opt) return
  selectedTown.value = { code: opt.value, name: opt.name }
  areaText.value = opt.name
}

const canExport = computed(() => {
  if (selectedLevel.value === 'township' && !selectedTown.value) return false
  if (!selectedLevel.value) return false
  if (selectedAttachments.value.length === 0) return false
  return true
})

const triggerDownload = (url) => {
  const link = document.createElement('a')
  link.href = encodeURI(url)
  link.setAttribute('download', '')
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const onBatchExport = async () => {
  exporting.value = true
  showProgressDialog.value = true
  taskPercent.value = 5
  targetPercent.value = 5
  taskMessage.value = '正在提交批量任务...'
  taskCompleted.value = false
  taskFailed.value = false
  stopPolling()

  try {
    const payload = {
      level: selectedLevel.value,
      township_code: selectedTown.value ? selectedTown.value.code : '',
      township_name: selectedTown.value ? selectedTown.value.name : '',
      attachments: selectedAttachments.value
    }

    // 1. 发起请求，后端异步开启并瞬间返回 task_id，彻底规避 524 超时
    const res = await axios.post('/api/batch_export', payload)
    if (res.data.code !== 200 || !res.data.task_id) {
      taskFailed.value = true
      taskMessage.value = res.data.message || '启动批量打包任务失败'
      exporting.value = false
      return
    }

    const taskId = res.data.task_id

    // 2. 轮询任务进度
    pollTimer = setInterval(async () => {
      try {
        const progRes = await axios.get(`/api/batch_export/progress?task_id=${taskId}`)
        if (progRes.data.code === 200 && progRes.data.data) {
          const info = progRes.data.data
          targetPercent.value = info.percent || 0
          taskPercent.value = info.percent || 0
          if (info.message) {
            taskMessage.value = info.message
          }

          if (info.status === 'completed') {
            stopPolling()
            taskCompleted.value = true
            exporting.value = false
            if (info.url) {
              triggerDownload(info.url)
              showToast({ type: 'success', message: '打包成功！已触发下载' })
            }
          } else if (info.status === 'failed') {
            stopPolling()
            taskFailed.value = true
            exporting.value = false
            taskMessage.value = info.error || info.message || '打包过程异常中断'
            showToast({ type: 'fail', message: '打包失败' })
          }
        }
      } catch (pollErr) {
        console.warn('轮询进度出错，稍后继续重试...', pollErr)
      }
    }, 1500)

  } catch (e) {
    console.error(e)
    stopPolling()
    taskFailed.value = true
    exporting.value = false
    taskMessage.value = '请求服务器失败，请检查网络'
  }
}

onBeforeUnmount(() => {
  stopPolling()
})

onMounted(() => {
  initTowns()
})
</script>

<style scoped>
.page-body {
  padding: 16px 0;
}
.export-panel {
  padding: 16px;
  margin-top: 16px;
}
.dir-tip {
  font-size: 13px;
  color: #969799;
  text-align: center;
  margin-top: 12px;
  line-height: 1.5;
}
.progress-box {
  padding: 20px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
}
.progress-circle-wrap {
  margin-bottom: 16px;
}
.progress-info {
  margin-bottom: 12px;
}
.status-title {
  font-size: 16px;
  font-weight: 600;
  color: #323233;
  margin-bottom: 6px;
}
.error-text {
  color: #ee0a24 !important;
}
.current-step-msg {
  font-size: 13px;
  color: #646566;
  line-height: 1.6;
  min-height: 42px;
  word-break: break-all;
}
.progress-tip {
  font-size: 12px;
  color: #969799;
  margin-top: 8px;
  background: #f7f8fa;
  padding: 6px 12px;
  border-radius: 4px;
}
</style>
