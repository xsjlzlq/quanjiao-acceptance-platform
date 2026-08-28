<template>
  <div class="rectify">
    <van-nav-bar title="自查整改" left-text="返回" left-arrow @click-left="onBack" />
    <div class="page-body">
      <van-cell-group inset title="选择乡镇">
        <van-field
          v-model="areaText"
          label="乡镇"
          placeholder="请选择乡镇"
          readonly
          is-link
          @click="showPicker = true"
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
const showPicker = ref(false)
const pickerColumns = ref([])

const exporting12 = ref(false)
const exporting13 = ref(false)

const triggerDownload = (url) => {
  const link = document.createElement('a')
  link.href = encodeURI(url)
  link.setAttribute('download', '')
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const onBack = () => router.back()

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
      '&township_name=' + encodeURIComponent(selectedTown.value.name)
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
