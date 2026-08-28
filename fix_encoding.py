import os

files = {
    'frontend/index.html': '''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
    <title>全椒县县级验收管理平台</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>''',

    'frontend/src/views/Home.vue': '''<template>
  <div class="home">
    <van-nav-bar title="工作台 - 县级验收管理平台" />
    <div class="dashboard">
      <van-grid :column-num="2" clickable>
        <van-grid-item icon="todo-list-o" text="内业核查" to="/neiye" />
        <van-grid-item icon="location-o" text="外业核查" to="/waiye" />
        <van-grid-item icon="cluster-o" text="任务与抽样" to="/tasks" />
        <van-grid-item icon="bar-chart-o" text="得分评定" to="/score" />
        <van-grid-item icon="setting-o" text="系统设置" to="/settings" />
      </van-grid>
    </div>
  </div>
</template>

<style scoped>
.home {
  min-height: 100vh;
}
.dashboard {
  margin-top: 20px;
}
</style>''',

    'frontend/src/views/Tasks.vue': '''<template>
  <div class="tasks">
    <van-nav-bar title="自查申请与任务下发" left-arrow @click-left="$router.back()" />
    
    <van-tabs v-model:active="activeTab" sticky>
      <van-tab title="乡镇申请">
        <van-cell-group inset style="margin-top:16px;">
          <van-cell title="襄河镇" label="农户: 2134户 | 确权面积: 3.5万亩" center>
            <template #right-icon>
              <van-button size="small" type="primary">受理校验</van-button>
            </template>
          </van-cell>
          <van-cell title="十字镇" label="农户: 1890户 | 确权面积: 2.8万亩" center>
            <template #right-icon>
              <van-button size="small" type="warning">资料不全</van-button>
            </template>
          </van-cell>
        </van-cell-group>
      </van-tab>
      
      <van-tab title="抽样管理">
        <van-cell-group inset title="抽样规则配置" style="margin-top:16px;">
          <van-field label="发包方数量" placeholder="每个镇 2~5 个" />
          <van-field label="农户抽检比例" placeholder="每个发包方 5%" />
        </van-cell-group>
        <div style="margin: 16px;">
          <van-button round block type="primary" @click="generateSamples">生成抽样清单 (全县>20)</van-button>
        </div>
      </van-tab>
    </van-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { showToast } from 'vant';

const activeTab = ref(0);

const generateSamples = () => {
  showToast({ type: 'success', message: '已成功生成抽样统计表并下发外业任务' });
};
</script>'''
}

for path, content in files.items():
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
print('Fixed Home.vue, Tasks.vue, index.html')
