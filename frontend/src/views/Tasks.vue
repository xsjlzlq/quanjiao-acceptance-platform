<template>
  <div class="tasks">
    <van-nav-bar title="自查申请与任务下发" left-arrow @click-left="$router.back()" />
    
    <van-tabs v-model:active="activeTab" sticky>
      <!-- ================= 标签页 1：进度看板 ================= -->
      <van-tab title="进度看板" v-if="hasPerm('tasks_dashboard')">
        <!-- 顶部全局汇总统计卡片 -->
        <div class="dashboard-header-card" v-if="dashboardStats">
          <div class="dash-title-row">
            <span class="dash-county-tag">{{ dashboardStats.county_name }}验收进度总览</span>
            <van-button size="mini" plain type="primary" icon="replay" :loading="loadingDashboard" @click="fetchProgressDashboard">
              刷新看板
            </van-button>
          </div>
          
          <div class="dash-grid-stats">
            <div class="dash-stat-item">
              <div class="stat-value text-primary">
                {{ dashboardStats.sampled_townships_count }} <span class="stat-unit">/ {{ dashboardStats.total_townships }} 镇</span>
              </div>
              <div class="stat-desc">已抽样乡镇覆盖</div>
            </div>
            <div class="dash-stat-item">
              <div class="stat-value" :class="dashboardStats.is_groups_compliant ? 'text-success' : 'text-danger'">
                {{ dashboardStats.sampled_groups_count }} <span class="stat-unit">个</span>
              </div>
              <div class="stat-desc">抽样发包方组数 (≥20组)</div>
            </div>
            <div class="dash-stat-item">
              <div class="stat-value text-warning">
                {{ dashboardStats.sampled_farmers_count }} <span class="stat-unit">户</span>
              </div>
              <div class="stat-desc">抽查承包农户总数</div>
            </div>
            <div class="dash-stat-item">
              <div class="stat-value text-info">
                {{ dashboardStats.sampled_parcels_count }} <span class="stat-unit">宗</span>
              </div>
              <div class="stat-desc">核验承包地块总数</div>
            </div>
          </div>

          <!-- 全县内外业总进度对比 -->
          <div class="global-progress-box">
            <div class="progress-row">
              <div class="prog-info">
                <span class="prog-name"><van-icon name="todo-list-o" /> 全县内业核查总进度</span>
                <span class="prog-text">{{ dashboardStats.neiye_completed_villages }} / {{ dashboardStats.neiye_total_villages }} 村 ({{ dashboardStats.neiye_percent }}%)</span>
              </div>
              <van-progress :percentage="dashboardStats.neiye_percent" stroke-width="6" color="#07c160" />
            </div>

            <div class="progress-row" style="margin-top: 10px;">
              <div class="prog-info">
                <span class="prog-name"><van-icon name="location-o" /> 全县外业签名总进度</span>
                <span class="prog-text">{{ dashboardStats.waiye_signed_farmers }} / {{ dashboardStats.waiye_total_farmers }} 户 ({{ dashboardStats.waiye_percent }}%)</span>
              </div>
              <van-progress :percentage="dashboardStats.waiye_percent" stroke-width="6" color="#1989fa" />
            </div>
          </div>
        </div>

        <!-- 空状态提示 -->
        <div v-if="!loadingDashboard && (!townshipProgressList || townshipProgressList.length === 0)" class="empty-dashboard">
          <van-empty description="当前数据库暂无已抽样乡镇数据" image="network">
            <van-button round type="primary" size="small" @click="activeTab = 2">去执行抽样</van-button>
          </van-empty>
        </div>

        <!-- 已抽样乡镇进度卡片列表 -->
        <div v-else class="township-cards-container">
          <div class="section-heading">
            <span>已抽样乡镇明细 (共 {{ townshipProgressList.length }} 个乡镇)</span>
            <span class="heading-tip">按村级呈现内业核查与外业核验</span>
          </div>

          <div
            v-for="item in townshipProgressList"
            :key="item.township_name"
            class="township-progress-card"
          >
            <!-- 头部 -->
            <div class="card-header">
              <div class="town-title">
                <span class="town-name">{{ item.township_name }}</span>
                <van-tag
                  :type="item.status_code === 'completed' ? 'success' : (item.status_code === 'in_progress' ? 'primary' : 'default')"
                  size="medium"
                  round
                >
                  {{ item.status_text }}
                </van-tag>
              </div>
              <div class="sample-badges">
                <span>{{ item.neiye.total_villages }} 村</span>
                <span class="dot">·</span>
                <span>{{ item.group_count }} 组</span>
                <span class="dot">·</span>
                <span>{{ item.farmer_count }} 户</span>
                <span class="dot">·</span>
                <span>{{ item.parcel_count }} 宗地块</span>
              </div>
            </div>

            <!-- 内业进度条与村级得分展示 -->
            <div class="sub-progress-section">
              <div class="section-sub-title">
                <div class="title-left">
                  <van-icon name="edit" color="#07c160" />
                  <strong>内业核查进度</strong>
                </div>
                <div class="title-right">
                  <span style="font-weight: bold; color: #07c160;">{{ item.neiye.completed_villages }} / {{ item.neiye.total_villages }} 村完成</span>
                  <span style="margin-left: 6px; color: #999;">({{ item.neiye.percent }}%)</span>
                </div>
              </div>
              <van-progress :percentage="item.neiye.percent" stroke-width="7" color="#07c160" />

              <!-- 抽样村明细药丸标签 -->
              <div class="village-pills" v-if="item.neiye.village_details && item.neiye.village_details.length > 0">
                <div
                  v-for="v in item.neiye.village_details"
                  :key="v.village_code"
                  class="village-pill"
                  :class="v.completed ? 'is-done' : 'is-pending'"
                  @click="$router.push('/neiye')"
                >
                  <span class="v-status-icon">{{ v.completed ? '✓' : '⏳' }}</span>
                  <span class="v-name">{{ v.village_name }}</span>
                  <span class="v-score" v-if="v.completed">{{ v.score }}分</span>
                  <span class="v-score-pending" v-else>待核查</span>
                </div>
              </div>
            </div>

            <!-- 外业核查进度与现况展示 -->
            <div class="sub-progress-section" style="margin-top: 14px;">
              <div class="section-sub-title">
                <div class="title-left">
                  <van-icon name="location" color="#1989fa" />
                  <strong>外业核查进度</strong>
                </div>
                <div class="title-right">
                  <span style="font-weight: bold; color: #1989fa;">{{ item.waiye.signed_farmers }} / {{ item.waiye.total_farmers }} 户已签名</span>
                  <span style="margin-left: 6px; color: #999;">({{ item.waiye.percent }}%)</span>
                </div>
              </div>
              <van-progress :percentage="item.waiye.percent" stroke-width="7" color="#1989fa" />

              <div class="waiye-score-metrics">
                <div class="metric-tag">
                  <span>程序规范估算分：</span>
                  <strong style="color: #1989fa;">{{ item.waiye.prog_score }}分</strong>
                  <span class="metric-max">/20</span>
                </div>
                <div class="metric-tag">
                  <span>满意度估算分：</span>
                  <strong style="color: #ff976a;">{{ item.waiye.effect_score }}分</strong>
                  <span class="metric-max">/10</span>
                </div>
              </div>
            </div>

            <!-- 卡片底部快捷操作 -->
            <div class="card-footer-actions">
              <van-button size="small" plain type="success" icon="edit" to="/neiye">
                内业核查
              </van-button>
              <van-button size="small" plain type="primary" icon="location-o" to="/waiye">
                外业核查
              </van-button>
            </div>
          </div>
        </div>
      </van-tab>

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

          <template v-if="sGroupCode">
            <van-cell title="承包方总户数" :value="cbfCount + ' 户'" />
            <van-cell title="已抽样农户数">
              <template #value>
                <div style="display: inline-flex; align-items: center; gap: 8px;">
                  <van-tag :type="sampledCbfCount > 0 ? 'success' : 'default'" size="medium">
                    {{ sampledCbfCount }} 户
                  </van-tag>
                  <van-button 
                    v-if="sampledCbfCount > 0 && hasPerm('tasks_delete_contractor')"
                    size="mini" 
                    type="primary" 
                    plain 
                    round
                    style="height: 24px; padding: 0 8px; font-size: 12px;"
                    @click="openSampledContractorsDialog"
                  >
                    管理/删除
                  </van-button>
                </div>
              </template>
            </van-cell>
            <van-cell title="剩余可抽农户" :value="remainingCbfCount + ' 户'">
              <template #value>
                <van-tag :type="remainingCbfCount === 0 ? 'danger' : 'primary'" size="medium">
                  {{ remainingCbfCount }} 户
                </van-tag>
              </template>
            </van-cell>

            <div v-if="sampledCbfCount > 0 && remainingCbfCount > 0" style="padding: 6px 16px; font-size: 12px; color: #e6a23c; background: #fdf6ec; line-height: 1.5;">
              <van-icon name="info-o" style="margin-right: 4px;" />
              该组已存在 {{ sampledCbfCount }} 户抽样数据。本次手动抽样将自动排除已抽农户，进行增量补抽，并保留历史外业记录。
            </div>

            <div v-else-if="remainingCbfCount === 0" style="padding: 6px 16px; font-size: 12px; color: #ee0a24; background: #fff2f0; line-height: 1.5;">
              <van-icon name="close" style="margin-right: 4px;" />
              该村民小组所有承包方（共 {{ cbfCount }} 户）已全部抽样，无法重复抽样！
            </div>
            
            <van-field 
              v-model="manualCount"
              type="digit"
              label="指定抽样数"
              :disabled="remainingCbfCount === 0"
              :placeholder="remainingCbfCount === 0 ? '已全部抽样' : `留空默认抽样，最多可抽 ${remainingCbfCount} 户`"
            />
          </template>
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

          <!-- 数据写入策略单选 -->
          <van-cell title="写入模式">
            <template #value>
              <van-radio-group v-model="excelStrategy" direction="horizontal">
                <van-radio name="append">增量补抽</van-radio>
                <van-radio name="overwrite">覆盖重抽</van-radio>
              </van-radio-group>
            </template>
          </van-cell>
          <div style="padding: 4px 16px 10px; font-size: 12px; line-height: 1.5;">
            <span v-if="excelStrategy === 'append'" style="color: #07c160;">
              🟢 <strong>增量补抽</strong>：自动排除已抽农户并增量补齐，保留已有外业核查数据。
            </span>
            <span v-else style="color: #ee0a24;">
              🔴 <strong>覆盖重抽</strong>：清空表格中所列村组的全部既有抽样并重新随机抽取。
            </span>
          </div>

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
                <span>抽样规范核验通过：共检查 {{ excelCheckResult.total_groups }} 个发包方，指定户数均满足组级规范要求。</span>
              </div>
              <div v-if="excelCheckResult.exceeded_count > 0" style="font-size: 12px; color: #d48806; margin-top: 6px;">
                ℹ 提示：其中有 {{ excelCheckResult.exceeded_count }} 个发包方抽检数量高于建议抽样上限，属于严格检查，允许正常执行抽样。
              </div>
            </div>

            <!-- 村级 5% 抽查比例预警提示区 (机制 A: 醒目预警展示) -->
            <div v-if="excelCheckResult.has_village_warning" style="background: #fffbe6; border: 1px solid #ffe58f; border-radius: 8px; padding: 12px; margin-top: 10px;">
              <div style="display: flex; align-items: center; gap: 6px; color: #d48806; font-weight: bold; font-size: 13px; margin-bottom: 6px;">
                <van-icon name="warning-o" size="18" />
                <span>全村 5% 达标提醒：{{ excelCheckResult.village_warning_count }} 个行政村总抽检数未达到全村总户数的 5%</span>
              </div>
              <div style="font-size: 12px; color: #666; margin-bottom: 8px; line-height: 1.5;">
                验收规范建议每个抽验行政村抽查总农户数达到全村总户数的 5% 以上。以下行政村目前未达到 5%：
              </div>
              <div style="display: flex; flex-direction: column; gap: 6px; max-height: 200px; overflow-y: auto;">
                <div
                  v-for="(item, idx) in excelCheckResult.village_warnings"
                  :key="idx"
                  style="background: #fff; padding: 8px 10px; border-radius: 6px; border-left: 3px solid #faad14; font-size: 12px;"
                >
                  <div style="font-weight: bold; color: #333; margin-bottom: 3px;">
                    {{ idx + 1 }}. {{ item.village_desc }}
                  </div>
                  <div style="color: #666; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 4px;">
                    <span>全村总户数: <strong>{{ item.total_village_cbf }}</strong> 户 | 计划: <strong style="color: #d48806;">{{ item.sample_count }}</strong> 户 ({{ item.rate_pct }}%)</span>
                    <van-tag type="warning" size="medium">建议补抽 {{ item.shortage }} 户</van-tag>
                  </div>
                </div>
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

        <!-- 指定小组已抽样农户管理弹窗 -->
        <van-popup 
          v-model:show="showContractorsDialog" 
          round 
          position="bottom" 
          :style="{ height: '70%', display: 'flex', flexDirection: 'column' }"
          closeable
        >
          <div style="padding: 16px 16px 8px; font-size: 16px; font-weight: bold; border-bottom: 1px solid #f2f3f5;">
            <span>已抽样农户管理</span>
            <span style="font-size: 12px; font-weight: normal; color: #969799; margin-left: 8px;">
              ({{ sTownshipName }} {{ sVillageName }} {{ sGroupName }})
            </span>
          </div>

          <!-- 模糊搜索框 -->
          <van-search
            v-model="contractorSearchKeyword"
            placeholder="输入姓名或编码缩略码模糊检索"
            shape="round"
            @input="onSearchContractor"
          />

          <!-- 农户列表展示区域 -->
          <div style="flex: 1; overflow-y: auto; padding: 0 12px;">
            <van-empty 
              v-if="filteredSampledContractors.length === 0" 
              description="未找到匹配的已抽样农户" 
              image="search"
            />
            <div 
              v-else 
              v-for="item in pagedSampledContractors" 
              :key="item.cbfbm"
              style="display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; margin-bottom: 8px; background: #f7f8fa; border-radius: 6px;"
            >
              <div style="display: flex; align-items: center; gap: 10px;">
                <van-tag type="primary" plain size="medium" style="font-family: monospace;">
                  {{ item.cbfbm_short || item.cbfbm.slice(-4) }}
                </van-tag>
                <span style="font-size: 15px; font-weight: 600; color: #323233;">
                  {{ item.cbfmc }}
                </span>
              </div>
              <van-button 
                v-if="hasPerm('tasks_delete_contractor')"
                size="mini" 
                type="danger" 
                plain 
                round
                :loading="deletingCbfbm === item.cbfbm"
                style="padding: 0 10px;"
                @click="onDeleteContractor(item)"
              >
                删除
              </van-button>
            </div>
          </div>

          <!-- 分页器控制区域 -->
          <div 
            v-if="filteredSampledContractors.length > contractorPageSize" 
            style="padding: 10px 16px; border-top: 1px solid #f2f3f5; background: #fff;"
          >
            <van-pagination
              v-model="contractorCurrentPage"
              :total-items="filteredSampledContractors.length"
              :items-per-page="contractorPageSize"
              mode="simple"
            />
            <div style="text-align: center; font-size: 12px; color: #969799; margin-top: 4px;">
              共 {{ filteredSampledContractors.length }} 户，每页显示 {{ contractorPageSize }} 户
            </div>
          </div>
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
const sampledCbfCount = ref(0);
const remainingCbfCount = ref(0);
const manualCount = ref('');
const fileList = ref([]);
const excelStrategy = ref('append'); // 'append' 增量补抽 | 'overwrite' 覆盖重抽
const files = ref([]);

// 已抽样农户弹窗管理状态
const showContractorsDialog = ref(false);
const sampledContractorsList = ref([]);
const contractorSearchKeyword = ref('');
const contractorCurrentPage = ref(1);
const contractorPageSize = ref(8); // 每页固定显示 8 个农户
const deletingCbfbm = ref('');

// 模糊搜索过滤
const filteredSampledContractors = computed(() => {
  const kw = (contractorSearchKeyword.value || '').trim().toLowerCase();
  if (!kw) return sampledContractorsList.value;
  return sampledContractorsList.value.filter(item => {
    const nameMatch = item.cbfmc && item.cbfmc.toLowerCase().includes(kw);
    const shortMatch = item.cbfbm_short && item.cbfbm_short.toLowerCase().includes(kw);
    const fullMatch = item.cbfbm && item.cbfbm.toLowerCase().includes(kw);
    return nameMatch || shortMatch || fullMatch;
  });
});

// 分页截取展示
const pagedSampledContractors = computed(() => {
  const start = (contractorCurrentPage.value - 1) * contractorPageSize.value;
  return filteredSampledContractors.value.slice(start, start + contractorPageSize.value);
});

const onSearchContractor = () => {
  contractorCurrentPage.value = 1;
};

const openSampledContractorsDialog = async () => {
  if (!sGroupCode.value) return;
  showLoadingToast({ message: '加载已抽农户...', forbidClick: true });
  try {
    const res = await axios.get('/api/sample/group_contractors?group_code=' + sGroupCode.value);
    if (res.data.code === 200) {
      sampledContractorsList.value = res.data.data || [];
      contractorSearchKeyword.value = '';
      contractorCurrentPage.value = 1;
      showContractorsDialog.value = true;
    } else {
      showToast(res.data.message || '加载农户失败');
    }
  } catch (err) {
    showToast('网络异常，获取农户列表失败');
  } finally {
    closeToast();
  }
};

const onDeleteContractor = (item) => {
  const shortCode = item.cbfbm_short || item.cbfbm.slice(-4);
  showConfirmDialog({
    title: '删除抽样农户确认',
    message: `确定要将农户【${item.cbfmc}】(编码:${shortCode}) 从当前抽样数据中移除吗？\n移除后该户在地块核查中将被清除，并可重新增量补抽。`,
    confirmButtonText: '确认删除',
    confirmButtonColor: '#ee0a24'
  }).then(async () => {
    deletingCbfbm.value = item.cbfbm;
    try {
      const res = await axios.post('/api/sample/delete_contractor', {
        group_code: sGroupCode.value,
        cbfbm: item.cbfbm
      });
      if (res.data.code === 200) {
        showToast({ type: 'success', message: res.data.message || '已成功移除该农户' });
        
        // 1. 从弹窗本地数组中剔除
        sampledContractorsList.value = sampledContractorsList.value.filter(x => x.cbfbm !== item.cbfbm);
        
        // 如果当前页删空且不是第1页，自动退到前一页
        const maxPage = Math.ceil(filteredSampledContractors.value.length / contractorPageSize.value) || 1;
        if (contractorCurrentPage.value > maxPage) {
          contractorCurrentPage.value = maxPage;
        }

        // 2. 刷新外层该组统计数字
        const resCount = await axios.get('/api/contractor_count?group_code=' + sGroupCode.value);
        cbfCount.value = resCount.data.count || 0;
        sampledCbfCount.value = resCount.data.sampled_count || 0;
        remainingCbfCount.value = resCount.data.remaining_count || 0;

        // 3. 刷新全县抽样进度看板
        await fetchProgressDashboard();

        // 如果全部删空，自动关闭弹窗
        if (sampledContractorsList.value.length === 0) {
          showContractorsDialog.value = false;
        }
      } else {
        showToast(res.data.message || '删除失败');
      }
    } catch (e) {
      showToast('删除请求失败，请检查网络');
    } finally {
      deletingCbfbm.value = '';
    }
  }).catch(() => {});
};

// 进度看板状态管理
const loadingDashboard = ref(false);
const dashboardStats = ref(null);
const townshipProgressList = ref([]);

const fetchProgressDashboard = async () => {
  loadingDashboard.value = true;
  try {
    const res = await axios.get('/api/tasks/progress_dashboard');
    if (res.data && res.data.code === 200 && res.data.data) {
      dashboardStats.value = res.data.data.global_stats;
      townshipProgressList.value = res.data.data.township_list || [];
    }
  } catch (e) {
    console.error('获取进度看板失败', e);
  } finally {
    loadingDashboard.value = false;
  }
};

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
  if (hasPerm('tasks_dashboard')) {
    await fetchProgressDashboard();
  }
});

const onConfirmTp = (opt) => {
  sTownshipName.value = opt.selectedOptions[0].text;
  sTownshipCode.value = opt.selectedOptions[0].value;
  showTp.value = false;
  sVillageName.value = ''; sVillageCode.value = '';
  sGroupName.value = ''; sGroupCode.value = '';
  cbfCount.value = 0; sampledCbfCount.value = 0; remainingCbfCount.value = 0; manualCount.value = '';
};

const onConfirmVp = (opt) => {
  sVillageName.value = opt.selectedOptions[0].text;
  sVillageCode.value = opt.selectedOptions[0].value;
  showVp.value = false;
  sGroupName.value = ''; sGroupCode.value = '';
  cbfCount.value = 0; sampledCbfCount.value = 0; remainingCbfCount.value = 0; manualCount.value = '';
};

const onConfirmGp = async (opt) => {
  sGroupName.value = opt.selectedOptions[0].text;
  sGroupCode.value = opt.selectedOptions[0].full;
  showGp.value = false;
  const res = await axios.get('/api/contractor_count?group_code=' + sGroupCode.value);
  cbfCount.value = res.data.count || 0;
  sampledCbfCount.value = res.data.sampled_count || 0;
  remainingCbfCount.value = res.data.remaining_count || 0;
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
  if (mode.value === 1) {
    if (!sGroupCode.value) { showToast('请先选择到村民组'); return; }
    if (remainingCbfCount.value === 0) {
      showToast('该组所有承包方已全部抽样，无法继续抽样！');
      return;
    }
  }
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
        title: '发包方抽样数不达标拦截',
        message: `表格中检测到 ${excelCheckResult.value.insufficient_count} 个发包方的抽样数量低于组级验收规范要求，系统已强制拦截：\n\n${errListText}\n\n请在 Excel 表格中补足对应发包方的抽样户数后重新上传！`,
        messageAlign: 'left',
        confirmButtonText: '我知道了'
      });
      return;
    }

    // 机制 A：村级抽查总数未达到全村总户数 5% 友好预警确认提示
    if (excelCheckResult.value && excelCheckResult.value.has_village_warning) {
      const warnListText = excelCheckResult.value.village_warnings
        .map((it, i) => `${i + 1}. ${it.summary_text}`)
        .join('\n\n');
      try {
        await showConfirmDialog({
          title: '行政村抽样比例预警',
          message: `检测到以下 ${excelCheckResult.value.village_warning_count} 个行政村所抽农户总数未达到该村总户数的 5%：\n\n${warnListText}\n\n是否确认仍按当前表格继续执行抽样？`,
          confirmButtonText: '继续执行抽样',
          cancelButtonText: '暂缓，修改表格',
          confirmButtonColor: '#1989fa',
          messageAlign: 'left'
        });
      } catch {
        return; // 用户点击了“暂缓，修改表格”
      }
    }

    const formData = new FormData();
    formData.append('file', fileList.value[0].file);
    formData.append('strategy', excelStrategy.value);
    
    loading.value = true;
    try {
      const res = await axios.post('/api/sample_by_excel', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 120000
      });
    if (res.data.code === 200) {
      if (res.data.village_warnings && res.data.village_warnings.length > 0) {
        showToast({ type: 'success', message: '抽样成功！请注意部分村未达5%线', duration: 3000 });
      } else {
        showToast({ type: 'success', message: '抽样成功！抽样数据已保存至外业核查。' });
      }
      await fetchProgressDashboard();
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
      console.error('抽样失败异常:', e);
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
        const msg = errData?.message || (e.message && e.message.includes('timeout') ? '请求超时，数据量较大请重试' : '请求失败，请检查网络或后端服务');
        showToast(msg);
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
        await fetchProgressDashboard();
        // 刷新当前选定组的已抽/剩余户数
        if (mode.value === 1 && sGroupCode.value) {
          const resCount = await axios.get('/api/contractor_count?group_code=' + sGroupCode.value);
          cbfCount.value = resCount.data.count || 0;
          sampledCbfCount.value = resCount.data.sampled_count || 0;
          remainingCbfCount.value = resCount.data.remaining_count || 0;
          manualCount.value = '';
        }
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
        await fetchProgressDashboard();
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

<style scoped>
.dashboard-header-card {
  margin: 14px 16px;
  padding: 16px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.dash-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.dash-county-tag {
  font-size: 15px;
  font-weight: bold;
  color: #323233;
}

.dash-grid-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}

.dash-stat-item {
  background: #f7f8fa;
  padding: 10px 12px;
  border-radius: 8px;
}

.stat-value {
  font-size: 18px;
  font-weight: bold;
  line-height: 1.2;
}

.stat-unit {
  font-size: 11px;
  font-weight: normal;
  color: #666;
}

.stat-desc {
  font-size: 11px;
  color: #888;
  margin-top: 4px;
}

.text-primary { color: #1989fa; }
.text-success { color: #07c160; }
.text-warning { color: #ff976a; }
.text-danger  { color: #ee0a24; }
.text-info    { color: #7232dd; }

.global-progress-box {
  padding-top: 12px;
  border-top: 1px dashed #ebedf0;
}

.progress-row .prog-info {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 4px;
}

.prog-name {
  color: #333;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 4px;
}

.prog-text {
  color: #666;
  font-weight: bold;
}

.empty-dashboard {
  padding: 40px 0;
}

.township-cards-container {
  padding: 0 16px 20px;
}

.section-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 14px 4px 10px;
  font-size: 13px;
  font-weight: bold;
  color: #323233;
}

.heading-tip {
  font-size: 11px;
  font-weight: normal;
  color: #999;
}

.township-progress-card {
  background: #fff;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.card-header {
  border-bottom: 1px solid #f2f3f5;
  padding-bottom: 10px;
  margin-bottom: 12px;
}

.town-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.town-name {
  font-size: 16px;
  font-weight: bold;
  color: #323233;
}

.sample-badges {
  font-size: 12px;
  color: #666;
  margin-top: 4px;
}

.sample-badges .dot {
  margin: 0 4px;
  color: #ccc;
}

.sub-progress-section {
  background: #fafafa;
  border-radius: 8px;
  padding: 10px 12px;
}

.section-sub-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  margin-bottom: 6px;
}

.section-sub-title .title-left {
  display: flex;
  align-items: center;
  gap: 4px;
}

.village-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.village-pill {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 12px;
  font-size: 11px;
  cursor: pointer;
}

.village-pill.is-done {
  background: #eaf8ee;
  color: #07c160;
  border: 1px solid #c1ebd0;
}

.village-pill.is-pending {
  background: #f2f3f5;
  color: #888;
  border: 1px solid #e0e0e0;
}

.v-score {
  font-weight: bold;
}

.waiye-score-metrics {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 11px;
  color: #666;
}

.metric-max {
  font-size: 10px;
  color: #999;
}

.card-footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed #ebedf0;
}
</style>