<template>
  <div class="settings">
    <van-nav-bar
      title="系统设置"
      left-text="返回"
      left-arrow
      @click-left="$router.back()"
    >
      <template #right>
        <van-button size="mini" plain type="danger" @click="onLogout">退出登录</van-button>
      </template>
    </van-nav-bar>

    <van-tabs v-model:active="activeTab" sticky color="#1989fa">
      <!-- ================= 标签页 1：自动保存 ================= -->
      <van-tab title="自动保存" v-if="hasPerm('settings_autosave')">
        <van-cell-group inset title="核查状态自动保存配置" style="margin-top: 16px;">
          <van-cell center title="启用核查自动保存" label="开启后内业与外业核查将按设定间隔定时自动保存至数据库">
            <template #right-icon>
              <van-switch v-model="autoSaveEnabled" size="22" @change="onAutoSaveToggle" />
            </template>
          </van-cell>

          <van-field
            v-if="autoSaveEnabled"
            v-model="autoSaveInterval"
            type="digit"
            label="自动保存间隔"
            placeholder="请输入分钟数 (默认5分钟)"
          >
            <template #extra>
              <span>分钟 (默认5分钟)</span>
            </template>
          </van-field>

          <div style="margin: 16px;">
            <van-button round block type="primary" plain @click="saveAutoSaveConfig(true)">
              保存自动保存设置
            </van-button>
          </div>

          <div class="setting-tip">
            <strong>功能说明：</strong><br/>
            1. 开启后，进入「内业核查」或「外业核查」页面时，系统将在后台自动定时保存最新评分与打X核查状态到数据库。<br/>
            2. 默认时间间隔为 <strong>5 分钟</strong>，可根据实际网络环境与作业习惯自行调整。<br/>
            3. 关闭后，核查页面顶部将提示手动保存，不再执行定时后台保存。
          </div>
        </van-cell-group>
      </van-tab>

      <!-- ================= 标签页 2：权限设置（管理员专享） ================= -->
      <van-tab title="权限设置" v-if="isAdmin">
        <!-- 账号新增区 -->
        <van-cell-group inset title="新增账号" style="margin-top: 16px;">
          <van-field v-model="newUsername" label="用户名" placeholder="请输入新用户名" />
          <div style="display: flex; gap: 8px; margin: 12px 16px;">
            <van-button size="small" type="primary" style="flex:1" @click="onAddSingleUser">添加单账号</van-button>
            <van-uploader :after-read="onImportTxt" accept=".txt">
              <van-button size="small" type="default">导入txt批量新增</van-button>
            </van-uploader>
          </div>
          <div class="setting-tip">
            批量导入说明：txt 文件每行一个用户名，初始密码统一为 <strong>123456</strong>。
          </div>
        </van-cell-group>

        <!-- 账号列表 & 细粒度功能权限开关 -->
        <van-cell-group inset title="账号与细化功能权限管理" style="margin-top: 16px;">
          <div v-if="usersList.length === 0" style="text-align:center; padding:20px; color:#999;">
            加载中...
          </div>
          <template v-for="u in usersList" :key="u.username">
            <van-collapse v-model="activeCollapse">
              <van-collapse-item :name="u.username">
                <template #title>
                  <div style="display: flex; align-items: center; gap: 8px;">
                    <van-tag :type="u.role === 'admin' ? 'primary' : 'default'">
                      {{ u.role === 'admin' ? '管理员' : '普通用户' }}
                    </van-tag>
                    <strong>{{ u.username }}</strong>
                  </div>
                </template>
                <template #value>
                  <van-button
                    v-if="u.username !== 'admin'"
                    size="mini"
                    type="danger"
                    plain
                    @click.stop="onDeleteUser(u.username)"
                    style="margin-right: 4px;"
                  >删除</van-button>
                  <van-button
                    size="mini"
                    type="warning"
                    plain
                    @click.stop="onResetPassword(u.username)"
                  >重置密码</van-button>
                </template>

                <!-- 模块细粒度权限列表 -->
                <div style="padding: 4px 0;">
                  <div v-for="mod in PERM_MODULES" :key="mod.title" style="margin-bottom: 12px;">
                    <div style="font-size: 13px; font-weight: bold; color: #1989fa; margin: 8px 0 4px;">
                      {{ mod.title }}
                    </div>
                    <van-cell
                      v-for="item in mod.items"
                      :key="item.key"
                      :title="item.label"
                      center
                      style="padding: 4px 8px; background: #fafafa; border-radius: 4px; margin-bottom: 4px;"
                    >
                      <template #right-icon>
                        <van-switch
                          v-model="u.perms[item.key]"
                          size="18"
                          :disabled="u.username === 'admin'"
                          @change="onPermChange(u)"
                        />
                      </template>
                    </van-cell>
                  </div>
                </div>
              </van-collapse-item>
            </van-collapse>
          </template>
        </van-cell-group>
      </van-tab>

      <!-- ================= 标签页 3：安全设置 ================= -->
      <van-tab title="安全设置" v-if="hasPerm('settings_security')">
        <van-cell-group inset title="修改登录密码" style="margin-top: 16px;">
          <van-cell title="当前登录账号" :value="currentUsername" />
          <van-field
            v-model="oldPassword"
            type="password"
            label="原密码"
            placeholder="请输入当前密码"
          />
          <van-field
            v-model="newPassword"
            type="password"
            label="新密码"
            placeholder="请输入新密码（至少6位）"
          />
          <van-field
            v-model="confirmPassword"
            type="password"
            label="确认新密码"
            placeholder="请再次输入新密码"
          />
          <div style="margin: 16px;">
            <van-button round block type="primary" @click="onChangePassword">
              确认修改密码
            </van-button>
          </div>
        </van-cell-group>
      </van-tab>

      <!-- ================= 标签页 4：数据入库 ================= -->
      <van-tab title="数据入库" v-if="hasPerm('settings_import')">
        <van-cell-group inset title="全量数据包入库" style="margin-top: 16px;">
          <van-field
            v-model="sourcePath"
            label="数据包路径"
            placeholder="例如: G:\全椒县二轮延包\全椒县县级验收管理平台\sources\341124100"
            required
          />
          <div style="margin: 16px;">
            <van-button round block type="primary" :loading="loading" loading-text="导入中..." @click="startImport">
              开始导入入库
            </van-button>
          </div>
          <div class="setting-tip">
            <strong>入库说明：</strong><br/>
            支持从指定目录读取权属代码表、地块矢量、承包方等核心业务数据包并写入系统数据库。
          </div>
        </van-cell-group>

        <van-cell-group inset title="执行日志" v-if="logs.length > 0" style="margin-top: 16px;">
          <van-cell v-for="(log, idx) in logs" :key="idx" :title="log" />
        </van-cell-group>
      </van-tab>
    </van-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { showToast, showDialog, showConfirmDialog } from 'vant';
import axios from 'axios';
import { hasPerm } from '../utils/auth';

const router = useRouter();
const activeTab = ref(0);
const activeCollapse = ref([]);

const AUTO_SAVE_KEY = 'auto_save_settings';
const autoSaveEnabled = ref(true);
const autoSaveInterval = ref('5');

const sourcePath = ref('G:\\全椒县二轮延包\\全椒县县级验收管理平台\\sources\\341124100');
const loading = ref(false);
const logs = ref([]);

// 细粒度功能权限分组定义：调换一与三顺序，补齐系统设置安全设置子项
const PERM_MODULES = [
  {
    title: '一、任务与抽样',
    items: [
      { key: 'tasks_sample',      label: '执行地块抽样' },
      { key: 'tasks_clear',       label: '清空抽样数据' },
      { key: 'tasks_export_att4', label: '导出附件4（抽样明细）' },
      { key: 'tasks_export_att5', label: '导出附件5（抽查汇总）' },
    ]
  },
  {
    title: '二、外业核查',
    items: [
      { key: 'waiye_check',       label: '外业核查与签名' },
      { key: 'waiye_save',        label: '保存核查状态' },
      { key: 'waiye_export_att8', label: '导出附件8（外业核查表）' },
      { key: 'waiye_export_att9', label: '导出附件9（县级核查表）' },
    ]
  },
  {
    title: '三、内业核查',
    items: [
      { key: 'neiye_view',        label: '查看与评分核查' },
      { key: 'neiye_save',        label: '保存核查状态' },
      { key: 'neiye_export_att6', label: '导出附件6（检查记录表）' },
      { key: 'neiye_export_att7', label: '导出附件7（检查得分表）' },
    ]
  },
  {
    title: '四、得分评定',
    items: [
      { key: 'score_view',        label: '查看综合得分' },
      { key: 'score_export_att10',label: '导出附件10（得分汇总表）' },
      { key: 'score_export_att11',label: '导出附件11（验收评定表）' },
    ]
  },
  {
    title: '五、自查整改',
    items: [
      { key: 'rectify_view',        label: '查看问题台账' },
      { key: 'rectify_export_att12',label: '导出附件12（整改通知书）' },
      { key: 'rectify_export_att13',label: '导出附件13（整改销号台账）' },
    ]
  },
  {
    title: '六、系统设置',
    items: [
      { key: 'settings_autosave', label: '自动保存配置' },
      { key: 'settings_security', label: '安全设置（修改密码）' },
      { key: 'settings_import',   label: '全量数据入库' },
    ]
  }
];

const currentUsername = computed(() => localStorage.getItem('auth_username') || '');
const isAdmin = computed(() => localStorage.getItem('auth_role') === 'admin');

// 权限管理数据
const usersList = ref([]);
const newUsername = ref('');

// 安全设置数据
const oldPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');

onMounted(async () => {
  try {
    const raw = localStorage.getItem(AUTO_SAVE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      autoSaveEnabled.value = parsed.enabled !== false;
      autoSaveInterval.value = String(parsed.interval || 5);
    }
  } catch (e) {}

  if (isAdmin.value) {
    await fetchUsers();
  }
});

const fetchUsers = async () => {
  try {
    const res = await axios.get('/api/auth/user_perms_all');
    if (res.data.code === 200) {
      usersList.value = res.data.users;
    }
  } catch (e) {}
};

// ── 自动保存 ─────────────────────────────────────────────────────────────
const onAutoSaveToggle = () => saveAutoSaveConfig(false);

const saveAutoSaveConfig = (showMsg = true) => {
  let interval = parseInt(autoSaveInterval.value);
  if (isNaN(interval) || interval <= 0) interval = 5;
  localStorage.setItem(AUTO_SAVE_KEY, JSON.stringify({
    enabled: autoSaveEnabled.value,
    interval
  }));
  if (showMsg) {
    showToast(autoSaveEnabled.value ? `设置已保存：每 ${interval} 分钟自动保存一次` : '已关闭自动保存');
  }
};

// ── 权限设置 ─────────────────────────────────────────────────────────────
const onAddSingleUser = async () => {
  const u = newUsername.value.trim();
  if (!u) { showToast('请输入用户名'); return; }
  try {
    const res = await axios.post('/api/auth/create_user', { username: u });
    if (res.data.code === 200) {
      showToast({ type: 'success', message: `账号 ${u} 添加成功（初始密码 123456）` });
      newUsername.value = '';
      await fetchUsers();
    } else {
      showToast(res.data.message || '添加失败');
    }
  } catch (e) { showToast('网络异常'); }
};

const onImportTxt = async (file) => {
  try {
    const text = await file.file.text();
    const names = text.split(/[\r\n]+/).map(s => s.trim()).filter(Boolean);
    if (names.length === 0) { showToast('txt 文件为空'); return; }
    const res = await axios.post('/api/auth/batch_create', { usernames: names });
    if (res.data.code === 200) {
      const okCount = res.data.results.filter(r => r.ok).length;
      showToast({ type: 'success', message: `批量导入成功：新增 ${okCount}/${names.length} 个账号` });
      await fetchUsers();
    }
  } catch (e) { showToast('读取文件失败'); }
};

const onDeleteUser = (username) => {
  showConfirmDialog({ title: '确认删除', message: `确定要删除账号 ${username} 吗？` })
    .then(async () => {
      const res = await axios.post('/api/auth/delete_user', { username });
      if (res.data.code === 200) {
        showToast('已删除');
        await fetchUsers();
      } else {
        showToast(res.data.message || '删除失败');
      }
    }).catch(() => {});
};

const onResetPassword = (username) => {
  showConfirmDialog({ title: '重置密码', message: `将账号 ${username} 的密码重置为 123456 吗？` })
    .then(async () => {
      const res = await axios.post('/api/auth/reset_password', { username, new_password: '123456' });
      if (res.data.code === 200) {
        showToast({ type: 'success', message: `账号 ${username} 密码已重置为 123456` });
      }
    }).catch(() => {});
};

const onPermChange = async (user) => {
  try {
    await axios.post('/api/auth/set_perms', {
      username: user.username,
      perms: user.perms
    });
    if (user.username === currentUsername.value) {
      localStorage.setItem('auth_perms', JSON.stringify(user.perms));
    }
    showToast({ type: 'success', message: '权限已更新' });
  } catch (e) { showToast('保存权限失败'); }
};

// ── 安全设置 ─────────────────────────────────────────────────────────────
const onChangePassword = async () => {
  if (!oldPassword.value) { showToast('请输入原密码'); return; }
  if (!newPassword.value || newPassword.value.length < 6) { showToast('新密码长度不能少于6位'); return; }
  if (newPassword.value !== confirmPassword.value) { showToast('两次新密码输入不一致'); return; }

  try {
    const res = await axios.post('/api/auth/change_password', {
      username: currentUsername.value,
      old_password: oldPassword.value,
      new_password: newPassword.value,
    });
    if (res.data.code === 200) {
      showToast({ type: 'success', message: '密码修改成功，请重新登录' });
      setTimeout(onLogout, 1500);
    } else {
      showToast(res.data.message || '修改失败');
    }
  } catch (e) { showToast('网络异常'); }
};

// ── 退出登录 ─────────────────────────────────────────────────────────────
const onLogout = () => {
  localStorage.removeItem('auth_token');
  localStorage.removeItem('auth_username');
  localStorage.removeItem('auth_role');
  localStorage.removeItem('auth_perms');
  router.push('/login');
};

// ── 数据入库 ─────────────────────────────────────────────────────────────
const startImport = async () => {
  if (!sourcePath.value) { showToast('请输入数据包路径'); return; }
  loading.value = true;
  logs.value = ['请求已发送，后端正在处理大数据入库，请耐心等待...'];
  try {
    const res = await axios.post('/api/import-data', { source_path: sourcePath.value });
    if (res.data.code === 200) {
      logs.value = res.data.details || ['导入成功'];
      showToast('数据包入库成功');
    } else {
      logs.value = [res.data.message];
      showDialog({ title: '入库失败', message: res.data.message });
    }
  } catch (err) {
    logs.value = ['请求异常: ' + err.message];
    showToast('网络或服务异常');
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.settings {
  min-height: 100vh;
  background-color: #f7f8fa;
  padding-bottom: 40px;
}
.setting-tip {
  padding: 0 16px 14px 16px;
  font-size: 12px;
  color: #969799;
  line-height: 1.6;
}
</style>