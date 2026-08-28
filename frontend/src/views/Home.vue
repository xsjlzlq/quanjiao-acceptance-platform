<template>
  <div class="home">
    <van-nav-bar title="工作台 - 县级验收管理平台">
      <template #right>
        <span class="user-badge" @click="goToSettings">
          <van-icon name="user-o" style="margin-right: 4px;" />
          {{ currentUsername }}
        </span>
      </template>
    </van-nav-bar>
    <div class="dashboard">
      <van-grid :column-num="2" clickable>
        <van-grid-item
          v-if="hasModulePerm('settings')"
          icon="setting-o"
          text="系统设置"
          to="/settings"
        />
        <van-grid-item
          v-if="hasModulePerm('tasks')"
          icon="cluster-o"
          text="任务与抽样"
          to="/tasks"
        />
        <van-grid-item
          v-if="hasModulePerm('waiye')"
          icon="location-o"
          text="外业核查"
          to="/waiye"
        />
        <van-grid-item
          v-if="hasModulePerm('neiye')"
          icon="todo-list-o"
          text="内业核查"
          to="/neiye"
        />
        <van-grid-item
          v-if="hasModulePerm('score')"
          icon="bar-chart-o"
          text="得分评定"
          to="/score"
        />
        <van-grid-item
          v-if="hasModulePerm('rectify')"
          icon="records"
          text="自查整改"
          to="/rectify"
        />
      </van-grid>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { hasPerm } from '../utils/auth';

const router = useRouter();
const currentUsername = computed(() => localStorage.getItem('auth_username') || '用户');

// 判断模块下是否有任一子权限
const hasModulePerm = (mod) => {
  const role = localStorage.getItem('auth_role');
  if (role === 'admin') return true;

  const MOD_PERMS = {
    settings: ['settings_autosave', 'settings_security', 'settings_import'],
    tasks:    ['tasks_sample', 'tasks_clear', 'tasks_export_att4', 'tasks_export_att5'],
    waiye:    ['waiye_check', 'waiye_save', 'waiye_export_att8', 'waiye_export_att9'],
    neiye:    ['neiye_view', 'neiye_save', 'neiye_export_att6', 'neiye_export_att7'],
    score:    ['score_view', 'score_export_att10', 'score_export_att11'],
    rectify:  ['rectify_view', 'rectify_export_att12', 'rectify_export_att13'],
  };

  const keys = MOD_PERMS[mod] || [];
  return keys.some(k => hasPerm(k));
};

const goToSettings = () => {
  router.push('/settings');
};
</script>

<style scoped>
.home {
  min-height: 100vh;
  background-color: #f7f8fa;
}
.dashboard {
  margin-top: 16px;
  padding: 0 8px;
}
.user-badge {
  font-size: 13px;
  color: #1989fa;
  cursor: pointer;
  display: flex;
  align-items: center;
}
</style>