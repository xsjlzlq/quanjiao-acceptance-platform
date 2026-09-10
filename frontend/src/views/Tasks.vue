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
                <van-uploader accept=".pdf,image/*" result-type="file" :after-read="(file) => uploadAppForm(file, ts)">
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
                <van-radio :name="1">按村组手动抽样</van-radio>
                <van-radio :name="2">按乡镇自动抽组及农户</van-radio>
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
            placeholder="为空则按系统规则默认抽样"
          />
        </van-cell-group>

        <!-- Mode 3: Excel Upload -->
        <van-cell-group inset title="上传抽样表格 (方式三)" v-if="mode === 3" style="margin-top: 16px;">
          <van-cell title="上传文件">
            <template #label>
              <van-uploader
                v-model="fileList"
                accept=".xls,.xlsx"
                result-type="file"
                max-count="1"
                :after-read="onExcelAfterRead"
                @delete="onExcelDelete"
              />
            </template>
          </van-cell>
          <div style="padding:0 16px; font-size:12px; color:#999; margin-bottom:10px;">
            表格需包含表头：发包方编码，乡镇名，村名，组名，抽样农户数。<br/>
            如填写了抽样农户数按实际抽取，留空则按系统规则默认抽样。
          </div>

          <!-- 表格预检加载状态 -->
          <div v-if="excelCheckLoading" style="padding: 10px 16px 14px; font-size: 13px; color: #1989fa; display: flex; align-items: center; gap: 6px;">
            <van-loading size="16px" />
            <span>正在核对各发包方指定抽样户数是否达标...</span>
          </div>

          <!-- 预检合规提醒卡片 -->
          <div v-else-if="excelCheckResult" style="margin: 0 16px 14px;">
            <!-- 存在抽样数不足 (强拦截红色警示区) -->
            <div v-if="excelCheckResult.has_insufficient" style="background: #fff2f0; border: 1px solid #ffccc7; border-radius: 8px; padding: 12px;">
              <div style="display: flex; align-items: center; gap: 6px; color: #cf1322; font-weight: bold; font-size: 14px; margin-bottom: 6px;">
                <van-icon name="clear" size="18" />
                <span>{{ excelCheckResult.insufficient_count }} 个发包方抽样数不达标（已禁止抽样）</span>
              </div>
              <div style="font-size: 12px; color: #666; margin-bottom: 8px; line-height: 1.5;">
                根据规范要求：总户数&lt;20户须全抽；20-100户至少抽5户；&gt;100户至少抽5%。以下发包方抽样数不足，已被系统强行拦截：
              </div>
              <div style="display: flex; flex-direction: column; gap: 6px; max-height: 240px; overflow-y: auto;">
                <div
                  v-for="(item, idx) in excelCheckResult.insufficient_list"
                  :key="idx"
                  style="background: #fff; padding: 8px 10px; border-radius: 6px; border-left: 3px solid #f5222d; font-size: 12px;"
                >
                  <div style="font-weight: bold; color: #333; margin-bottom: 3px;">
                    {{ idx + 1 }}. {{ item.group_desc }}
                  </div>
                  <div style="color: #666; display: flex; justify-content: space-between; align-items: center;">
                    <span>总户数: <strong>{{ item.total_cbf }}</strong> 户 | 指定: <strong style="color: #cf1322;">{{ item.specified_count }}</strong> 户 (最低需 {{ item.required_min }} 户)</span>
                    <van-tag type="danger" size="medium">缺少 {{ item.shortage }} 户</van-tag>
                  </div>
                </div>
              </div>
            </div>

            <!-- 全部发包方足额或留空 (绿色通过提示) -->
            <div v-else style="background: #f6ffed; border: 1px solid #b7eb8f; border-radius: 8px; padding: 12px;">
              <div style="display: flex; align-items: center; gap: 6px; color: #389e0d; font-weight: bold; font-size: 13px;">
                <van-icon name="checked" size="16" />
                <span>抽样规范核验通过：共检查 {{ excelCheckResult.total_groups }} 个发包方，指定户数均满足规范要求。</span>
              </div>
              <div v-if="excelCheckResult.exceeded_count > 0" style="font-size: 12px; color: #d48806; margin-top: 6px;">
                ℹ 提示：其中有 {{ excelCheckResult.exceeded_count }} 个发包方抽检数量高于建议抽样上限，属于严格检查，允许正常执行抽样。
              </div>
            </div>
          </div>
        </van-cell-group>

        <!-- Mode 2: Auto selection -->
        <van-cell-group inset title="选择抽样乡镇 (方式二)" v-if="mode === 2" style="margin-top: 16px;">
          <van-cell title="选择乡镇" is-link :value="selectedTownshipsText" @click="showTownshipMultiSelect = true" />
          <van-popup v-model:show="showTownshipMultiSelect" round position="bottom" style="max-height: 60%; display: flex; flex-direction: column;">
            <div style="padding: 10px 16px; font-weight: bold; text-align: center; border-bottom: 1px solid #eee;">请选择抽样乡镇</div>
            <div style="flex: 1; overflow-y: auto; padding: 10px 0;">
              <van-checkbox-group v-model="selectedTownshipCodes">
                <van-cell-group inset>
                  <van-cell v-for="t in townships" :key="t.code" :title="t.name" clickable @click="toggleTownship(t.code)">
                    <template #right-icon><van-checkbox :name="t.code" @click.stop /></template>
                  </van-cell>
                </van-cell-group>
              </van-checkbox-group>
            </div>
            <div style="padding: 12px;"><van-button block type="primary" @click="showTownshipMultiSelect = false">确定</van-button></div>
          </van-popup>
          <div style="padding:0 16px; font-size:12px; color:#999; margin-bottom:10px;">系统将根据全县乡镇总数自动决定每镇抽组数（≥10个乡镇抽2-5组，&lt;10个乡镇抽3-6组），每组按规则抽样农户。</div>
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
import { showToast, showLoadingToast, showConfirmDialog, showDialog, closeToast } from 'vant';
import axios from 'axios';
import { hasPerm } from '../utils/auth';

const activeTab = ref(0);
const loading = ref(false);

const townships = ref([]);
const villages = ref([]);
const groups = ref([]);
const countyData = ref(null);

const combinedTownships = computed(() => {
  const cName = countyData.value ? countyData.value.name : '全县';
  const cCode = countyData.value ? countyData.value.code : '341124';
  const cFull = countyData.value ? countyData.value.full_code : (cCode + '00000000');
  return [
    { name: `${cName} (县级)`, code: cCode, full_code: cFull, level: 'county' },
    ...townships.value
  ];
});

const uploadAppForm = async (file, ts) => {
  showLoadingToast({ message: '上传中...', forbidClick: true });
  try {
    const formData = new FormData();
    let actualFile = Array.isArray(file) ? file[0] : file; actualFile = actualFile.file || actualFile; formData.append('file', actualFile);
    formData.append('township_name', ts.name);
    formData.append('township_code', ts.full_code);
    const res = await axios.post('/api/upload_appform', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    closeToast();
    if (res.data.code === 200) {
      showToast({ type: 'success', message: '上传成功' });
    } else {
      showToast(res.data.message || '上传失败');
    }
  } catch(e) {
    closeToast();
    showToast('网络异常');
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

const showTownshipMultiSelect = ref(false);
const selectedTownshipCodes = ref([]);

const toggleTownship = (code) => {
  const index = selectedTownshipCodes.value.indexOf(code);
  if (index > -1) {
    selectedTownshipCodes.value.splice(index, 1);
  } else {
    selectedTownshipCodes.value.push(code);
  }
};

const selectedTownshipsText = computed(() => {
  if (selectedTownshipCodes.value.length === 0) return '请选择';
  return `已选择 ${selectedTownshipCodes.value.length} 个`;
});

const selectedTownshipNames = computed(() => {
  return selectedTownshipCodes.value.map(code => {
    const t = townships.value.find(x => x.code === code);
    return t ? t.name : '';
  });
});

const cbfCount = ref(0);
const manualCount = ref('');
const fileList = ref([]);
const files = ref([]);

// 方式三：Excel 表格抽样合规性预检状态
const excelCheckLoading = ref(false);
const excelCheckResult = ref(null);

const onExcelAfterRead = async (file) => {
  excelCheckResult.value = null;
  excelCheckLoading.value = true;
  const actualFile = file.file || file;
  const formData = new FormData();
  formData.append('file', actualFile);
  try {
    const res = await axios.post('/api/sample_by_excel/check', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    if (res.data.code === 200) {
      excelCheckResult.value = res.data.data;
      if (res.data.data.has_insufficient) {
        showToast({
          type: 'fail',
          message: `发现 ${res.data.data.insufficient_count} 个发包方抽样数不足！`
        });
      } else {
        showToast({
          type: 'success',
          message: '表格抽样数量规范核验通过！'
        });
      }
    } else {
      showToast(res.data.message || '表格核验失败');
    }
  } catch(e) {
    showToast('表格预检请求失败');
  } finally {
    excelCheckLoading.value = false;
  }
};

const onExcelDelete = () => {
  excelCheckResult.value = null;
  excelCheckLoading.value = false;
};

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
      countyData.value = res.data.county;
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
  if (mode.value === 2 && selectedTownshipCodes.value.length === 0) { showToast('请至少选择一个抽样乡镇'); return; }

  if (mode.value === 3) {
    if (fileList.value.length === 0) {
      showToast('请先上传表格文件');
      return;
    }

    // 抽样数不够强制拦截：如果预检已发现不足，直接弹窗阻断执行
    if (excelCheckResult.value && excelCheckResult.value.has_insufficient) {
      const errListText = excelCheckResult.value.insufficient_list
        .map((it, i) => `${i + 1}. ${it.summary_text}`)
        .join('\n\n');
      showDialog({
        title: '抽样数量不达标拦截提示',
        message: `表格中检测到 ${excelCheckResult.value.insufficient_count} 个发包方的抽样数量低于验收规范要求，系统已强制拦截：\n\n${errListText}\n\n请在 Excel 表格中补足对应发包方的抽样户数后重新上传！`,
        messageAlign: 'left',
        confirmButtonText: '我知道了'
      });
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
      } else {
        if (res.data.insufficient_list && res.data.insufficient_list.length > 0) {
          const detailMsg = res.data.insufficient_list.map((msg, i) => `${i + 1}. ${msg}`).join('\n\n');
          showDialog({
            title: '抽样数量不达标拦截提示',
            message: `表格中检测到发包方抽样数量低于验收规范要求，已被系统强制拦截：\n\n${detailMsg}\n\n请在表格中补足抽样户数后重新上传！`,
            messageAlign: 'left',
            confirmButtonText: '我知道了'
          });
        } else {
          showToast(res.data.message || '抽样异常');
        }
      }
    } catch(e) {
      const errData = e.response?.data;
      if (errData && errData.insufficient_list && errData.insufficient_list.length > 0) {
        const detailMsg = errData.insufficient_list.map((msg, i) => `${i + 1}. ${msg}`).join('\n\n');
        showDialog({
          title: '抽样数量不达标拦截提示',
          message: `表格中检测到发包方抽样数量低于验收规范要求，已被系统强制拦截：\n\n${detailMsg}\n\n请在表格中补足抽样户数后重新上传！`,
          messageAlign: 'left',
          confirmButtonText: '我知道了'
        });
      } else {
        showToast(errData?.message || '请求失败');
      }
    } finally { loading.value = false; }
    return;
  }

  loading.value = true;
  try {
    const res = await axios.post('/api/sample', {
      mode: mode.value,
      township_code: mode.value === 2 ? (selectedTownshipCodes.value[0] || '') : sTownshipCode.value,
      village_code: sVillageCode.value,
      group_code: sGroupCode.value,
      township_name: mode.value === 2 ? (selectedTownshipNames.value[0] || '') : sTownshipName.value,
      village_name: sVillageName.value,
      group_name: sGroupName.value,
      manual_sample_count: manualCount.value ? parseInt(manualCount.value) : null,
      township_codes: mode.value === 2 ? selectedTownshipCodes.value : null,
      township_names: mode.value === 2 ? selectedTownshipNames.value : null
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