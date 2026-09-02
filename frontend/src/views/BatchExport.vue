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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { showToast, showLoadingToast, closeToast } from 'vant'

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

const countyAttachments = [
  { id: 'att6_county', name: '附件6：县级自查内业组检查记录表' },
  { id: 'att7', name: '附件7：县级自查内业组检查得分表' },
  { id: 'att9', name: '附件9：县级自查外业组检查得分表' },
  { id: 'att10', name: '附件10：县级自查得分汇总表' },
  { id: 'att11', name: '附件11：县级自查验收评定表' }
]

const townshipAttachments = [
  { id: 'att4', name: '附件4：成果检查验收申请表' },
  { id: 'att5', name: '附件5：自查抽样统计表' },
  { id: 'att6_township', name: '附件6：县级自查内业组检查记录表' },
  { id: 'att8', name: '附件8：外业核查记录表' },
  { id: 'inquiry', name: '附件：询问笔录（该镇所有已填报农户）' },
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

const onBatchExport = async () => {
  exporting.value = true
  showLoadingToast({ message: '正在批量打包生成中，耗时较长请耐心等待...', forbidClick: true, duration: 0 })
  try {
    const payload = {
      level: selectedLevel.value,
      township_code: selectedTown.value ? selectedTown.value.code : '',
      township_name: selectedTown.value ? selectedTown.value.name : '',
      attachments: selectedAttachments.value
    }
    const res = await axios.post('/api/batch_export', payload, { timeout: 600000 }) // 10 min timeout
    if (res.data.code === 200 && res.data.url) {
      showToast({ type: 'success', message: '打包成功！开始下载...', duration: 3000 })
      triggerDownload(res.data.url)
    } else {
      showToast({ type: 'fail', message: res.data.message || '生成打包文件失败', duration: 3000 })
    }
  } catch (e) {
    console.error(e)
    showToast({ type: 'fail', message: '服务器响应超时或异常' })
  } finally {
    closeToast()
    exporting.value = false
  }
}

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
</style>
