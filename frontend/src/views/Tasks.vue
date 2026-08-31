<template>
  <div class="tasks">
    <van-nav-bar title="自查申请与任务下发" left-arrow @click-left="$router.back()" />
    
    <van-tabs v-model:active="activeTab" sticky>
      <van-tab title="自查申请">
        <van-cell-group inset style="margin-top:16px;">
          <van-cell 
            v-for="ts in combinedTownships" 
            :key="ts.full_code" 
            :title="ts.name" 
            :label="`权属代码: ${ts.full_code}`" 
            center
          >
            <template #right-icon>
              <div style="display: flex; gap: 8px;">
                <van-button size="small" plain type="primary" @click="generateAtt4(ts)">下载申请表</van-button>
                <van-uploader accept=".pdf,image/*" :after-read="(file) => uploadAppForm(file, ts)">
                  <van-button size="small" type="success">上传扫描件</van-button>
                </van-uploader>
              </div>
            </template>
          </van-cell>
        </van-cell-group>
      </van-tab>
      
      <van-tab title="抽样管理">
        <van-cell-group inset title="抽样模式" style="margin-top:16px;">
          <van-field name="mode" label="抽样方式">
            <template #input>
              <van-radio-group v-model="mode" direction="horizontal">
                <van-radio :name="1">按村组手动抽样5%</van-radio>
                <van-radio :name="2">按乡镇自动抽组及5%农户</van-radio>
                <van-radio :name="3">按导入表格抽样</van-radio>
              </van-radio-group>
            </template>
          </van-field>
        </van-cell-group>

        <!-- Mode 1: Manual selection -->
        <van-cell-group inset title="组别定位 (方式一)" v-if="mode === 1" style="margin-top: 16px;">
          <van-field v-model="sTownshipName" is-link readonly label="乡镇" placeholder="请选择" @click="showTp = true" />
          <van-popup v-model:show="showTp" round position="bottom"><van-picker :columns="tpCols" @cancel="showTp = false" @confirm="onConfirmTp" /></van-popup>

          <van-field v-model="sVillageName" is-link readonly label="村级" placeholder="请选择" @click="showVp = true" :disabled="!sTownshipCode" />
          <van-popup v-model:show="showVp" round position="bottom"><van-picker :columns="vpCols" @cancel="showVp = false" @confirm="onConfirmVp" /></van-popup>

          <van-field v-model="sGroupName" is-link readonly label="村组" placeholder="请选择" @click="showGp = true" :disabled="!sVillageCode" />
          <van-popup v-model:show="showGp" round position="bottom"><van-picker :columns="gpCols" @cancel="showGp = false" @confirm="onConfirmGp" /></van-popup>

          <van-cell title="该组承包方数量" :value="cbfCount + ' 户'" v-if="sGroupCode" />
          
          <van-field 
            v-if="sGroupCode"
            v-model="manualCount"
            type="digit"
            label="指定抽样数"
            placeholder="为空则默认按 5% 向上取整抽样"
          />
        </van-cell-group>

        <!-- Mode 3: Excel Upload -->
        <van-cell-group inset title="上传抽样表格 (方式三)" v-if="mode === 3" style="margin-top: 16px;">
          <van-cell title="上传文件">
            <template #label>
              <van-uploader v-model="fileList" accept=".xls,.xlsx" max-count="1" />
            </template>
          </van-cell>
          <div style="padding:0 16px; font-size:12px; color:#999; margin-bottom:10px;">
            表格需包含表头：发包方编码，乡镇名，村名，组名，抽样农户数。<br/>
            如填写了抽样农户数按实际抽取，留空则默认按 5% 向上取整抽取。
          </div>
        </van-cell-group>

        <!-- Mode 2: Auto selection -->
        <van-cell-group inset title="选择抽样乡镇 (方式二)" v-if="mode === 2" style="margin-top: 16px;">
          <van-field v-model="sTownshipName" is-link readonly label="乡镇" placeholder="请选择" @click="showTp = true" />
          <van-popup v-model:show="showTp" round position="bottom"><van-picker :columns="tpCols" @cancel="showTp = false" @confirm="onConfirmTp" /></van-popup>
          <div style="padding:0 16px; font-size:12px; color:#999; margin-bottom:10px;">系统将在此乡镇内随机选择2-5个组，并在每个组随机抽样5%的承包方(向上取整)。</div>
        </van-cell-group>

        <!-- 操作按钮组：开始抽样 + 清空抽样 -->
        <div style="margin: 16px; display: flex; gap: 10px;">
          <van-button 
            v-if="hasPerm('tasks_sample')"
            round 
            block 
            type="primary" 
            :loading="loading" 
            @click="generateSamples" 
            style="flex: 2;"
          >
            开始抽样并生成统计表
          </van-button>
          <van-button 
            v-if="hasPerm('tasks_clear')"
            round 
            plain 
            type="danger" 
            @click="onClearSamples" 
            style="flex: 1;"
          >
            清空抽样
          </van-button>
        </div>

        <!-- 清空抽样范围选择弹窗（县级 / 乡镇级） -->
        <van-popup v-model:show="showClearPicker" round position="bottom">
          <van-picker
            title="选择清空抽样范围 (县级/乡镇级)"
            :columns="clearScopeColumns"
            @cancel="showClearPicker = false"
            @confirm="onConfirmClearScope"
          />
        </van-popup>

        <van-cell-group inset title="抽样结果文件 (附件5 抽样统计表)" v-if="files.length > 0" style="margin-top:16px; margin-bottom: 30px;">
          <van-cell v-for="(f, i) in files" :key="i" :title="f.name" is-link @click="downloadFile(f.url)" />
          <div style="padding: 10px 16px; font-size: 13px; color: #07c160;">
            ✓ 抽样数据已自动存入数据库！请前往「外业核查」模块查看抽样地块并进行现场打X与导出附件8。
          </div>
        </van-cell-group>

      </van-tab>
    </van-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { showToast, showLoadingToast, showConfirmDialog, closeToast } from 'vant';
import axios from 'axios';
import { hasPerm } from '../utils/auth';

const activeTab = ref(0);
const loading = ref(false);

const townships = ref([]);
const villages = ref([]);
const groups = ref([]);

const combinedTownships = computed(() => {
  return [
    { name: '全椒县 (县级)', code: '341124', full_code: '341124', level: 'county' },
    ...townships.value
  ];
});

const uploadAppForm = async (file, ts) => {
  showLoadingToast({ message: '上传中...', forbidClick: true });
  try {
    const formData = new FormData();
    formData.append('file', file.file);
    formData.append('township_name', ts.name);
    formData.append('township_code', ts.full_code);
    const res = await axios.post('/api/upload_appform', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    if (res.data.code === 200) {
      showToast({ type: 'success', message: '上传成功' });
    } else {
      showToast(res.data.message || '上传失败');
    }
  } catch(e) {
    showToast('网络异常');
  } finally {
    closeToast();
  }
};

const mode = ref(2);

const showTp = ref(false);
const showVp = ref(false);
const showGp = ref(false);
const showClearPicker = ref(false);

const sTownshipName = ref('');
const sTownshipCode = ref('');
const sVillageName = ref('');
const sVillageCode = ref('');
const sGroupName = ref('');
const sGroupCode = ref('');

const cbfCount = ref(0);
const manualCount = ref('');
const fileList = ref([]);
const files = ref([]);

const tpCols = computed(() => townships.value.map(t => ({ text: t.name, value: t.code, full: t.full_code })));
const vpCols = computed(() => villages.value.filter(v => v.parent === sTownshipCode.value).map(v => ({ text: v.name, value: v.code, full: v.full_code })));
const gpCols = computed(() => groups.value.filter(g => g.parent === sVillageCode.value).map(g => ({ text: g.name, value: g.code, full: g.full_code })));

// 清空范围选择列表：县级 + 10个乡镇级
const clearScopeColumns = computed(() => [
  { text: '县级 - 清空全县所有抽样数据', value: 'ALL', level: 'county', name: '全县' },
  ...townships.value.map(t => ({
    text: `${t.name} (乡镇级 - 仅清空该镇抽样)`,
    value: t.code,
    name: t.name,
    level: 'township'
  }))
]);

onMounted(async () => {
  showLoadingToast({ message: '加载中...', forbidClick: true });
  try {
    const res = await axios.get('/api/hierarchy');
    if (res.data.code === 200) {
      townships.value = res.data.townships;
      villages.value = res.data.villages;
      groups.value = res.data.groups;
    }
  } catch(e) {} finally { closeToast(); }
});

const onConfirmTp = (opt) => {
  sTownshipName.value = opt.selectedOptions[0].text;
  sTownshipCode.value = opt.selectedOptions[0].value;
  showTp.value = false;
  sVillageName.value = ''; sVillageCode.value = '';
  sGroupName.value = ''; sGroupCode.value = '';
  cbfCount.value = 0; manualCount.value = '';
};

const onConfirmVp = (opt) => {
  sVillageName.value = opt.selectedOptions[0].text;
  sVillageCode.value = opt.selectedOptions[0].value;
  showVp.value = false;
  sGroupName.value = ''; sGroupCode.value = '';
  cbfCount.value = 0; manualCount.value = '';
};

const onConfirmGp = async (opt) => {
  sGroupName.value = opt.selectedOptions[0].text;
  sGroupCode.value = opt.selectedOptions[0].full;
  showGp.value = false;
  const res = await axios.get('/api/contractor_count?group_code=' + sGroupCode.value);
  cbfCount.value = res.data.count || 0;
};

const generateAtt4 = async (ts) => {
  showLoadingToast({ message: '生成中...', forbidClick: true });
  try {
    const res = await axios.get(`/api/generate_att4?township_name=${ts.name}&township_code=${ts.full_code}`);
    if (res.data.code === 200) {
      downloadFile(res.data.url);
    } else {
      showToast(res.data.message || '生成失败');
    }
  } catch(e) { 
    showToast('生成失败'); 
  } finally {
    closeToast();
  }
};

const downloadFile = (url) => {
  window.open(url, '_blank');
};

const generateSamples = async () => {
  if (mode.value === 1 && !sGroupCode.value) { showToast('请先选择到村民组'); return; }
  if (mode.value === 2 && !sTownshipCode.value) { showToast('请选择抽样乡镇'); return; }

  if (mode.value === 3) {
    if (fileList.value.length === 0) {
      showToast('请先上传表格文件');
      return;
    }
    const formData = new FormData();
    formData.append('file', fileList.value[0].file);
    
    loading.value = true;
    try {
      const res = await axios.post('/api/sample_by_excel', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      if (res.data.code === 200) {
        showToast({ type: 'success', message: '抽样成功！抽样数据已保存至外业核查。' });
        files.value = res.data.urls.map(u => ({
          name: u.split('file=downloads/')[1],
          url: u
        }));
      } else { showToast(res.data.message || '抽样异常'); }
    } catch(e) {
      showToast('请求失败');
    } finally { loading.value = false; }
    return;
  }

  loading.value = true;
  try {
    const res = await axios.post('/api/sample', {
      mode: mode.value,
      township_code: sTownshipCode.value,
      village_code: sVillageCode.value,
      group_code: sGroupCode.value,
      township_name: sTownshipName.value,
      village_name: sVillageName.value,
      group_name: sGroupName.value,
      manual_sample_count: manualCount.value ? parseInt(manualCount.value) : null
    });
    if (res.data.code === 200) {
      showToast({ type: 'success', message: '抽样成功！抽样数据已保存至外业核查。' });
      files.value = res.data.urls.map(u => ({
        name: u.split('file=downloads/')[1],
        url: u
      }));
    } else { showToast(res.data.message || '抽样异常'); }
  } catch(e) {} finally { loading.value = false; }
};

// 点击清空抽样：唤起范围选择器
const onClearSamples = () => {
  showClearPicker.value = true;
};

// 确认清空所选范围（县级 / 乡镇级）
const onConfirmClearScope = ({ selectedOptions }) => {
  showClearPicker.value = false;
  if (!selectedOptions || selectedOptions.length === 0) return;
  const opt = selectedOptions[0];
  const isCounty = opt.level === 'county';
  const targetLabel = isCounty ? '【全县】' : `【${opt.name}】`;
  
  showConfirmDialog({
    title: '清空抽样数据确认',
    message: `确定要清空 ${targetLabel} 的抽样数据吗？清空后外业核查中对应的抽样记录将被清除。`
  }).then(async () => {
    showLoadingToast({ message: '正在清空...', forbidClick: true });
    try {
      const payload = isCounty 
        ? { level: 'county' } 
        : { level: 'township', township_code: opt.value, township_name: opt.name };
      const res = await axios.post('/api/sample/clear', payload);
      if (res.data.code === 200) {
        showToast({ type: 'success', message: res.data.message || `${targetLabel} 抽样数据已清空！` });
        // 如果清空的是全县或者当前选中的乡镇，清空界面结果
        if (isCounty || sTownshipCode.value === opt.value) {
          files.value = [];
          fileList.value = [];
          manualCount.value = '';
          sGroupName.value = '';
          sGroupCode.value = '';
          cbfCount.value = 0;
        }
      } else {
        showToast(res.data.message || '清空失败');
      }
    } catch(e) {
      showToast('清空请求失败');
    } finally {
      closeToast();
    }
  }).catch(() => {});
};
</script>