<template>
  <div class="score">
    <van-nav-bar title="自查得分汇总与评定" left-arrow @click-left="$router.back()" />
    
    <van-cell-group inset title="各分项得分">
      <van-cell title="内业 - 机制运行(15分)" :value="scoreData.mech + '分'" />
      <van-cell title="内业 - 程序规范(30分)" :value="scoreData.prog_nei + '分'" />
      <van-cell title="内业 - 政策落实(15分)" :value="scoreData.policy + '分'" />
      <van-cell title="内业 - 风险防范(10分)" :value="scoreData.effect_nei + '分'" />
      <van-cell title="外业 - 程序规范(20分)" :value="scoreData.prog_wai + '分'" />
      <van-cell title="外业 - 满意度(10分)" :value="scoreData.effect_wai + '分'" />
    </van-cell-group>

    <van-cell-group inset title="特殊情形扣分 (直接扣减总分)" style="margin-top:16px;">
      <van-cell center title="方案要求不严格 (扣0.5分)">
        <template #right-icon>
          <van-switch v-model="special1" size="20" />
        </template>
      </van-cell>
      <van-cell center title="走过场未反映真实情况 (扣1分)">
        <template #right-icon>
          <van-switch v-model="special2" size="20" />
        </template>
      </van-cell>
      <van-field name="stepper" label="未制定延包方案扣分">
        <template #input>
          <van-stepper v-model="special3" step="0.5" min="0" />
        </template>
      </van-field>
    </van-cell-group>

    <van-cell-group inset title="最终评定结果" style="margin-top:16px;">
      <van-cell title="自查总分" :value="finalScore + '分'" size="large" />
      <van-cell title="验收结果评定" :value="level" size="large" :value-class="levelColor" />
    </van-cell-group>

    <div style="margin: 16px;">
      <van-button v-if="hasPerm('score_export_att10')" round block type="primary" :loading="exporting10" @click="onOpenAtt10Sheet">导出附件10 (自查得分汇总表)</van-button>
      <van-button v-if="hasPerm('score_export_att11')" round block type="success" style="margin-top: 10px;" :loading="exporting11" @click="onOpenAtt11Sheet">导出附件11 (自查验收评定表)</van-button>
    </div>

    <!-- 导出附件10选项操作面板 -->
    <van-action-sheet
      v-model:show="showAtt10Sheet"
      :actions="severeFilterActions"
      cancel-text="取消"
      description="请选择附件10得分计算方式"
      close-on-click-action
      @select="onSelectAtt10Action"
    />

    <!-- 导出附件11选项操作面板 -->
    <van-action-sheet
      v-model:show="showAtt11Sheet"
      :actions="severeFilterActions"
      cancel-text="取消"
      description="请选择附件11得分计算方式"
      close-on-click-action
      @select="onSelectAtt11Action"
    />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { hasPerm } from '../utils/auth';
import { showToast, showConfirmDialog } from 'vant';

import axios from 'axios';

const scoreData = ref({
  mech: 0,
  prog_nei: 0,
  policy: 0,
  effect_nei: 0,
  prog_wai: 0,
  effect_wai: 0
});

const exporting10 = ref(false);
const exporting11 = ref(false);

const showAtt10Sheet = ref(false);
const showAtt11Sheet = ref(false);
const severeFilterActions = [
  { name: '严重问题参与计算得分', value: true, subname: '严重问题正常计入扣分（默认）' },
  { name: '严重问题不参与计算得分', value: false, subname: '严重问题不计入扣分，仅扣非严重问题' }
];

const onOpenAtt10Sheet = () => {
  showAtt10Sheet.value = true;
};

const onSelectAtt10Action = (action) => {
  if (action && typeof action.value === 'boolean') {
    onExportAtt10(action.value);
  }
};

const onOpenAtt11Sheet = () => {
  showAtt11Sheet.value = true;
};

const onSelectAtt11Action = (action) => {
  if (action && typeof action.value === 'boolean') {
    onExportAtt11(action.value);
  }
};

const special1 = ref(false);
const special2 = ref(false);
const special3 = ref(0);

onMounted(async () => {
  try {
    const res = await axios.get('/api/score/summary');
    if (res.data.code === 200) {
      scoreData.value = res.data.data;
    }
    const res2 = await axios.get('/api/special_deductions');
    if (res2.data.code === 200) {
      special1.value = res2.data.data.special1;
      special2.value = res2.data.data.special2;
      special3.value = res2.data.data.special3;
    }
  } catch (e) {
    console.error(e);
  }
});

watch([special1, special2, special3], async ([s1, s2, s3]) => {
  try {
    await axios.post('/api/special_deductions', {
      special1: s1,
      special2: s2,
      special3: s3
    });
  } catch (e) {
    console.error('保存特殊情形扣分失败', e);
  }
});

const onExportAtt10 = async (includeSevere = true) => {
  exporting10.value = true;
  try {
    const res = await axios.get('/api/export_att10?include_severe=' + includeSevere);
    if (res.data.code === 200 && res.data.url) {
      const link = document.createElement('a');
      link.href = res.data.url;
      link.download = '';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast({ type: 'success', message: '附件10已生成并下载' });
    }
  } catch(e) {
    showToast('生成附件10失败');
  } finally {
    exporting10.value = false;
  }
};

const onExportAtt11 = async (includeSevere = true) => {
  exporting11.value = true;
  try {
    const res = await axios.post('/api/export_att11', {
      special1: special1.value,
      special2: special2.value,
      special3: special3.value,
      include_severe: includeSevere
    });
    if (res.data.code === 200 && res.data.url) {
      const link = document.createElement('a');
      link.href = res.data.url;
      link.download = '';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      showToast({ type: 'success', message: '附件11已生成并下载' });
    }
  } catch(e) {
    showToast('生成附件11失败');
  } finally {
    exporting11.value = false;
  }
};



const finalScore = computed(() => {
  let total = Object.values(scoreData.value).reduce((a, b) => a + b, 0);
  let deduct = (special1.value ? 0.5 : 0) + (special2.value ? 1.0 : 0) + special3.value;
  total -= deduct;
  return total < 0 ? 0 : total.toFixed(1);
});




const level = computed(() => {
  const s = finalScore.value;
  if (s >= 90) return '优秀 (合格)';
  if (s >= 80) return '良好 (合格)';
  if (s >= 70) return '合格';
  return '不合格';
});

const levelColor = computed(() => {
  return finalScore.value >= 70 ? 'text-success' : 'text-danger';
});

</script>

<style scoped>
.text-success {
  color: #07c160;
  font-weight: bold;
}
.text-danger {
  color: #ee0a24;
  font-weight: bold;
}
</style>
