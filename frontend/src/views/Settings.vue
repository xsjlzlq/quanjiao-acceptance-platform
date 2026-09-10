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
      <!-- ================= 标签页 2：权限设置（管理员专享） ================= -->
      <van-tab title="权限设置" v-if="isAdmin">
        <!-- 账号新增区 -->
        <van-cell-group inset title="新增账号" style="margin-top: 16px;">
          <van-field v-model="newUsername" label="用户名" placeholder="请输入新用户名" />
          <div style="display: flex; gap: 8px; margin: 12px 16px;">
            <van-button size="small" type="primary" style="flex:1" @click="onAddSingleUser">添加账号</van-button>
            <van-uploader :after-read="onImportTxt" accept=".txt">
              <van-button size="small" type="default">批量添加</van-button>
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
        <!-- 当前系统数据库与快速切换卡片 -->
        <van-cell-group inset title="当前系统数据库 (config.json)" style="margin-top: 16px;">
          <van-cell title="当前连接数据库" :value="currentDbName">
            <template #label>
              <div style="font-size: 13px; color: #333; margin-top: 2px;">
                所属县域：<strong style="color: #1989fa;">{{ currentCounty }}</strong>
              </div>
              <div v-if="currentDbSummary && currentDbSummary.township_count > 0" style="color: #07c160; margin-top: 4px; font-size: 12px;">
                ✓ 统计：{{ currentDbSummary.township_count }} 个乡镇、{{ currentDbSummary.group_count }} 个村民组、{{ currentDbSummary.farmer_count }} 户农户、{{ currentDbSummary.parcel_count }} 宗地块
              </div>
              <div v-else style="color: #999; margin-top: 4px; font-size: 12px;">
                暂无权属数据或该库尚未导入
              </div>
            </template>
            <template #right-icon>
              <van-button size="small" type="primary" plain @click="showDbPicker = true" style="margin-left: 8px;">
                切换数据库
              </van-button>
            </template>
          </van-cell>
        </van-cell-group>

        <!-- 切换数据库 Picker 弹窗 -->
        <van-popup v-model:show="showDbPicker" round position="bottom">
          <van-picker
            title="选择要连接的系统数据库"
            :columns="availableDbs"
            @cancel="showDbPicker = false"
            @confirm="onConfirmSwitchDb"
          />
        </van-popup>

        <van-cell-group inset title="全量数据包入库与新建数据库" style="margin-top: 16px;">
          <van-field
            v-model="countyName"
            label="县域名称"
            placeholder="例如: 全椒县 (以此名称创建数据库)"
            required
            :disabled="loading"
          />
          <van-field
            v-model="sourcePath"
            label="数据包路径"
            placeholder="例如: \sources\341124100"
            required
            :disabled="loading"
          />

          <!-- 导入进度与状态展示 -->
          <div v-if="loading || progressPercent > 0" style="padding: 14px 16px;">
            <!-- 免常驻提示 -->
            <div v-if="loading" style="font-size: 12px; color: #ff976a; margin-bottom: 8px; display: flex; align-items: center; gap: 4px;">
              <van-icon name="info-o" />
              <span>入库在后台独立运行，页面无需常驻，可离开或关闭。操作已实时存入日志。</span>
            </div>

            <div style="display: flex; justify-content: space-between; font-size: 13px; margin-bottom: 6px;">
              <span style="color: #1989fa; font-weight: bold;">{{ progressMessage || '正在处理中...' }}</span>
              <span style="color: #666; font-weight: bold;">{{ progressPercent }}%</span>
            </div>
            
            <!-- 标准平滑进度条 -->
            <van-progress :percentage="progressPercent" stroke-width="8" color="#1989fa" />
          </div>

          <div style="margin: 16px;">
            <van-button round block type="primary" :loading="loading" loading-text="正在入库中..." @click="startImport">
              开始导入入库并初始化数据库
            </van-button>
          </div>
          <div class="setting-tip">
            <strong>入库说明与文件规范：</strong><br/>
            1. 输入的<strong>县域名称</strong>将自动作为系统底层数据库名（若不存在将自动创建）。<br/>
            2. <strong>数据包规范检查：</strong>数据包根目录下必须存在<strong>【权属数据】</strong>和<strong>【矢量数据】</strong>两个文件夹；<br/>
            &nbsp;&nbsp;&nbsp;• <strong>【权属数据】</strong>中必须存在 <code>.mdb</code> 权属数据库文件和权属单位代码表 (Excel表格 <code>.xls/.xlsx</code>)；<br/>
            &nbsp;&nbsp;&nbsp;• <strong>【矢量数据】</strong>中必须存在文件名包含 <code>*DK*</code> 的矢量文件 (如 <code>DK341124100.shp</code>)；<br/>
            3. 若文件夹缺失、命名不符或必要文件缺失，系统将立即拦截并提示具体错误原因；校验通过后自动入库并展示全县乡镇、村组及农户数量汇总。
          </div>
        </van-cell-group>

        <!-- 入库成果统计卡片 (仅在当前导入完成后展示，页面刷新后不再显示) -->
        <van-cell-group inset title="数据入库成果统计" v-if="showResultCards && importSummary" style="margin-top: 16px;">
          <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; padding: 14px;">
            <div class="stat-card" style="border-left: 4px solid #1989fa;">
              <div class="stat-num" style="color: #1989fa;">{{ importSummary.township_count }}</div>
              <div class="stat-label">乡镇数量</div>
            </div>
            <div class="stat-card" style="border-left: 4px solid #07c160;">
              <div class="stat-num" style="color: #07c160;">{{ importSummary.village_count }}</div>
              <div class="stat-label">行政村数量</div>
            </div>
            <div class="stat-card" style="border-left: 4px solid #ff976a;">
              <div class="stat-num" style="color: #ff976a;">{{ importSummary.group_count }}</div>
              <div class="stat-label">村民组数量</div>
            </div>
            <div class="stat-card" style="border-left: 4px solid #ee0a24;">
              <div class="stat-num" style="color: #ee0a24;">{{ importSummary.farmer_count }}</div>
              <div class="stat-label">承包农户总数</div>
            </div>
          </div>
          <van-cell title="承包地块总数" :value="importSummary.parcel_count + ' 宗'" />
          <van-cell v-if="importSummary.townships && importSummary.townships.length > 0" title="覆盖乡镇" :label="importSummary.townships.join('、')" />
        </van-cell-group>

        <!-- 执行日志卡片（仅在当前导入过程中或完成后展示，刷新页面后不再显示） -->
        <van-cell-group inset style="margin-top: 16px;" v-if="showResultCards || loading">
          <template #title>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span>执行日志 (实时同步)</span>
              <van-button size="mini" plain type="primary" icon="down" @click="downloadImportLog">
                下载日志文件 (import.log)
              </van-button>
            </div>
          </template>
          <div class="log-console">
            <div v-for="(log, idx) in logs" :key="idx" class="log-line">
              <span class="log-prefix">&gt;</span> {{ log }}
            </div>
            <div v-if="logs.length === 0" style="color: #999; text-align: center; padding: 20px 0;">
              暂无日志记录
            </div>
          </div>
          <div class="setting-tip" style="padding-top: 8px;">
            提示：所有入库操作已自动追加写入后台日志文件 <code>logs/import.log</code>，中途离开或重启均可下载追溯。
          </div>
        </van-cell-group>
      </van-tab>

      <!-- ================= 标签页 5：使用帮助 ================= -->
      <van-tab title="使用帮助">
        <van-cell-group inset title="使用手册与文档" style="margin-top: 16px;">
          <div v-if="helpFiles.length === 0" style="text-align:center; padding:30px; color:#999;">
            暂无帮助文档
          </div>
          <van-cell
            v-for="f in helpFiles"
            :key="f.name"
            :title="f.name"
            :label="formatSize(f.size)"
            is-link
            @click="previewHelpFile(f.name)"
          >
            <template #right-icon>
              <van-button size="mini" type="primary" plain @click.stop="downloadHelpFile(f.name)">下载</van-button>
            </template>
          </van-cell>
        </van-cell-group>
        <div class="setting-tip" style="margin-top: 12px;">
          点击文件名可在线预览，点击下载按钮可下载到本地。
        </div>
      </van-tab>

      <!-- 文件预览弹层 -->
      <van-overlay :show="previewVisible" @click="previewVisible = false" style="z-index: 2000;">
        <div class="preview-wrapper" @click.stop>
          <div class="preview-header">
            <span class="preview-title">{{ previewFileName }}</span>
            <van-icon name="cross" size="20" color="#fff" @click="previewVisible = false" style="cursor:pointer;" />
          </div>
          <iframe :src="previewUrl" class="preview-iframe" frameborder="0"></iframe>
        </div>
      </van-overlay>
    </van-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { showToast, showDialog, showConfirmDialog, showLoadingToast, closeToast } from 'vant';
import axios from 'axios';
import { hasPerm } from '../utils/auth';

const router = useRouter();
const activeTab = ref(0);
const activeCollapse = ref([]);

// 数据库配置与切换 (config.json)
const currentDbName = ref('minguang');
const currentCounty = ref('全椒县');
const availableDbs = ref([]);
const currentDbSummary = ref(null);
const showDbPicker = ref(false);

const fetchDbConfig = async () => {
  try {
    const res = await axios.get('/api/system/db_config');
    if (res.data.code === 200 && res.data.data) {
      currentDbName.value = res.data.data.current_db;
      currentCounty.value = res.data.data.county_name;
      countyName.value = res.data.data.county_name || res.data.data.current_db;
      if (res.data.data.base_dir) {
        sourcePath.value = `${res.data.data.base_dir}\\sources\\341124100`;
      }
      availableDbs.value = (res.data.data.available_dbs || []).map(db => ({
        text: db === currentDbName.value ? `${db} (当前使用)` : db,
        value: db
      }));
      currentDbSummary.value = res.data.data.summary;
    }
  } catch (e) {
    console.error('获取数据库配置失败', e);
  }
};

const onConfirmSwitchDb = ({ selectedOptions }) => {
  showDbPicker.value = false;
  if (!selectedOptions || selectedOptions.length === 0) return;
  const targetDb = selectedOptions[0].value;
  if (targetDb === currentDbName.value) {
    showToast('当前已连接该数据库');
    return;
  }
  showConfirmDialog({
    title: '确认切换系统数据库',
    message: `确定要将系统连接切换至数据库【${targetDb}】吗？`
  }).then(async () => {
    showLoadingToast({ message: '正在切换数据库连接...', forbidClick: true });
    try {
      const res = await axios.post('/api/system/switch_db', { db_name: targetDb });
      closeToast();
      if (res.data.code === 200) {
        showToast({ type: 'success', message: res.data.message });
        await fetchDbConfig();
      } else {
        showToast(res.data.message || '切换失败');
      }
    } catch (err) {
      closeToast();
      showToast('切换异常: ' + (err.response?.data?.message || err.message));
    }
  }).catch(() => {});
};

const countyName = ref('全椒县');
const sourcePath = ref('\\sources\\341182全椒县');
const loading = ref(false);
const logs = ref([]);
const progressPercent = ref(0);
const progressMessage = ref('');
const currentAction = ref('');
const importSummary = ref(null);
const showResultCards = ref(false);
let progressTimer = null;

// 下载日志文件
const downloadImportLog = () => {
  window.open('/api/import-log/download', '_blank');
};

// 轮询入库进度
const pollProgress = async () => {
  try {
    const res = await axios.get('/api/import-progress');
    if (res.data.code === 200 && res.data.data) {
      const p = res.data.data;
      
      if (p.is_running) {
        loading.value = true;
        progressPercent.value = p.percent || 0;
        progressMessage.value = p.message || '';
        currentAction.value = p.current_action || p.message || '';
        if (p.details && p.details.length > 0) {
          logs.value = p.details;
        }
        if (p.summary) {
          importSummary.value = p.summary;
        }
        if (!progressTimer) {
          progressTimer = setInterval(pollProgress, 1000);
        }
      } else {
        // 任务已结束
        if (progressTimer) {
          clearInterval(progressTimer);
          progressTimer = null;
        }
        if (loading.value) {
          loading.value = false;
          progressPercent.value = p.percent || 100;
          progressMessage.value = p.message || '';
          if (p.details && p.details.length > 0) {
            logs.value = p.details;
          }
          if (p.summary) {
            importSummary.value = p.summary;
          }
          if (p.percent === 100 && p.summary) {
            showResultCards.value = true;
            showToast({ type: 'success', message: '全量数据入库成功！' });
            await fetchDbConfig();
          } else if (p.error || p.percent === 100) {
            showResultCards.value = true;
            showDialog({ title: '入库未完成', message: p.error || '数据入库未完全成功，请检查执行日志' });
          }
        }
      }
    }
  } catch (e) {
    console.error('进度获取失败', e);
  }
};

// 帮助文件
const helpFiles = ref([]);
const fetchHelpFiles = async () => {
  try {
    const res = await axios.get('/api/help/files');
    if (res.data.code === 200) {
      helpFiles.value = res.data.files;
    }
  } catch (e) {}
};
const formatSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1024 / 1024).toFixed(1) + ' MB';
};
const downloadHelpFile = (name) => {
  window.open('/api/help/download?file=' + encodeURIComponent(name), '_blank');
};

// 文件预览
const previewVisible = ref(false);
const previewFileName = ref('');
const previewUrl = ref('');
const previewHelpFile = (name) => {
  previewFileName.value = name;
  previewUrl.value = '/api/help/preview?file=' + encodeURIComponent(name);
  previewVisible.value = true;
};

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
      { key: 'waiye_inquiry',     label: '现场问询填报' },
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
    title: '六、附件导出',
    items: [
      { key: 'batch_export', label: '附件一键批量导出' },
    ]
  },
  {
    title: '七、系统设置',
    items: [
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
  if (isAdmin.value) {
    await fetchUsers();
  }
  await fetchHelpFiles();
  await fetchDbConfig();
  await pollProgress();
});

const fetchUsers = async () => {
  try {
    const res = await axios.get('/api/auth/user_perms_all');
    if (res.data.code === 200) {
      usersList.value = res.data.users;
    }
  } catch (e) {}
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
  if (!countyName.value || !countyName.value.trim()) { showToast('请输入县域名称'); return; }
  if (!sourcePath.value || !sourcePath.value.trim()) { showToast('请输入数据包路径'); return; }
  
  loading.value = true;
  progressPercent.value = 3;
  progressMessage.value = '正在核验数据包规范性...';
  logs.value = ['正在启动后台入库任务...'];
  importSummary.value = null;
  showResultCards.value = false;

  try {
    const res = await axios.post('/api/import-data', {
      county_name: countyName.value.trim(),
      source_path: sourcePath.value.trim()
    });
    
    if (res.data.code === 200) {
      showToast({ type: 'success', message: '入库任务已启动！' });
      // 启动轮询
      if (progressTimer) clearInterval(progressTimer);
      progressTimer = setInterval(pollProgress, 1000);
      await pollProgress();
    } else {
      loading.value = false;
      showDialog({ title: '前置校验失败', message: res.data.message });
    }
  } catch (err) {
    loading.value = false;
    const msg = err.response?.data?.message || err.message;
    logs.value = ['请求异常: ' + msg];
    showDialog({ title: '启动失败', message: msg });
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
.stat-card {
  background: #f7f8fa;
  padding: 12px 14px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.stat-num {
  font-size: 22px;
  font-weight: bold;
  line-height: 1.2;
}
.stat-label {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

/* 终端风格的执行日志框 */
.log-console {
  background: #1e1e1e;
  color: #d4d4d4;
  font-family: Consolas, Menlo, Monaco, "Courier New", monospace;
  font-size: 12px;
  padding: 12px 14px;
  border-radius: 6px;
  max-height: 220px;
  overflow-y: auto;
  line-height: 1.6;
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.3);
}

.log-line {
  word-break: break-all;
  white-space: pre-wrap;
  padding: 2px 0;
}

.log-prefix {
  color: #07c160;
  font-weight: bold;
  margin-right: 4px;
}
</style>

<style>
.preview-wrapper {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  display: flex;
  flex-direction: column;
  background: #333;
}
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: #1989fa;
  color: #fff;
  flex-shrink: 0;
}
.preview-title {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 80%;
}
.preview-iframe {
  flex: 1;
  width: 100%;
  border: none;
}
</style>