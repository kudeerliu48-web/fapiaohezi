<template>
  <div class="workbench-page">
    <div class="workbench-header">
      <h1 class="title">发票调试工作台</h1>
      <p class="desc">面向发票识别链路调试、历史追踪与批次运营</p>
    </div>

    <el-row :gutter="12" class="overview-row">
      <el-col :span="3" v-for="card in overviewCards" :key="card.key">
        <el-card shadow="hover" class="overview-card">
          <div class="card-head">
            <div class="card-label">{{ card.label }}</div>
            <i :class="['card-icon', card.icon]" />
          </div>
          <div class="card-value">{{ card.value }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="operation-card" shadow="never">
      <el-tabs v-model="activeTab" class="upload-tabs">
        <!-- 图片上传 Tab -->
        <el-tab-pane label="图片上传" name="upload">
          <div
            class="upload-area"
            :class="{ dragover: dragOver }"
            @dragover.prevent="dragOver = true"
            @dragleave.prevent="dragOver = false"
            @drop.prevent="onDropFiles"
          >
            <input ref="uploadInput" class="hidden-input" type="file" multiple accept="image/*,.pdf" @change="onChooseFiles" />
            <div class="upload-text">
              <div class="main">拖拽发票文件到此区域，或点击按钮选择文件</div>
              <div class="sub">支持 JPG / PNG / PDF，单次可上传多文件，文件大小受后端限制</div>
            </div>
            <div class="upload-actions">
              <el-button type="primary" icon="el-icon-upload2" @click="$refs.uploadInput.click()">选择文件</el-button>
              <el-button :disabled="!pendingFiles.length" :loading="uploading" @click="submitBatchUpload">上传并创建批次</el-button>
            </div>
          </div>
        </el-tab-pane>

        <!-- 邮箱拉取 Tab -->
        <el-tab-pane label="邮箱拉取" name="email">
          <div class="email-panel">
            <div class="email-form">
              <el-form :inline="true" :model="emailForm" size="small">
                <el-form-item label="邮箱地址">
                  <el-input v-model="emailForm.mailbox" placeholder="请输入邮箱地址" style="width: 260px" />
                </el-form-item>
                <el-form-item label="授权码">
                  <el-input v-model="emailForm.authCode" placeholder="请输入授权码" type="password" show-password style="width: 240px" />
                </el-form-item>
                <el-form-item label="时间范围">
                  <el-select v-model="emailForm.rangeKey" placeholder="请选择">
                    <el-option label="最近 7 天" value="7d" />
                    <el-option label="最近 1 个月" value="1m" />
                    <el-option label="最近 3 个月" value="3m" />
                    <el-option label="最近 6 个月" value="6m" />
                    <el-option label="最近 12 个月" value="12m" />
                  </el-select>
                </el-form-item>
                <el-form-item label="自定义日期">
                  <el-date-picker
                    v-model="emailForm.customDateRange"
                    type="daterange"
                    unlink-panels
                    range-separator="至"
                    start-placeholder="开始日期"
                    end-placeholder="结束日期"
                    value-format="yyyy-MM-dd"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :loading="emailSubmitting" @click="startEmailPush">开始拉取</el-button>
                </el-form-item>
              </el-form>
            </div>

            <!-- 统计卡片 -->
            <div v-if="emailTask && emailTask.status !== 'not_found'" class="email-stats">
              <el-row :gutter="12">
                <el-col :span="4">
                  <div class="stat-card">
                    <div class="stat-label">已扫描邮件</div>
                    <div class="stat-value">{{ emailStats.scanned_emails }}</div>
                  </div>
                </el-col>
                <el-col :span="4">
                  <div class="stat-card">
                    <div class="stat-label">匹配邮件数</div>
                    <div class="stat-value">{{ emailStats.matched_emails }}</div>
                  </div>
                </el-col>
                <el-col :span="4">
                  <div class="stat-card">
                    <div class="stat-label">已下载附件</div>
                    <div class="stat-value">{{ emailStats.downloaded_attachments }}</div>
                  </div>
                </el-col>
                <el-col :span="4">
                  <div class="stat-card">
                    <div class="stat-label">已成功导入</div>
                    <div class="stat-value success">{{ emailStats.imported_invoices }}</div>
                  </div>
                </el-col>
                <el-col :span="4">
                  <div class="stat-card">
                    <div class="stat-label">已触发识别</div>
                    <div class="stat-value">{{ emailStats.recognized_invoices }}</div>
                  </div>
                </el-col>
                <el-col :span="4">
                  <div class="stat-card">
                    <div class="stat-label">失败数量</div>
                    <div class="stat-value error">{{ emailStats.failed_count }}</div>
                  </div>
                </el-col>
              </el-row>
            </div>

            <div v-if="emailTask && emailTask.status !== 'not_found'" class="email-stage-card">
              <div class="stage-line">当前状态：{{ emailTaskStatusLabel(emailTask.status) }}</div>
              <div class="stage-line">当前阶段：{{ emailStageLabel }}</div>
              <div class="stage-line">目标邮箱：{{ emailTask.mailbox_account || emailForm.mailbox || '-' }}</div>
              <div class="stage-line">邮箱文件夹：{{ emailTask.mailbox || emailTask.mailbox_folder || 'INBOX' }}</div>
              <div class="stage-line">日期模式：{{ emailTask.date_range_mode || '-' }}</div>
              <div class="stage-line">生效范围：{{ emailTask.start_date || '-' }} 至 {{ emailTask.end_date || '-' }}</div>
              <div class="stage-line" v-if="emailTask.current_email_subject">当前邮件：{{ emailTask.current_email_subject }}</div>
              <div class="stage-line" v-if="emailTask.current_attachment_name">当前附件：{{ emailTask.current_attachment_name }}</div>
            </div>

            <!-- 进度条 -->
            <div v-if="emailTask && emailTask.status !== 'not_found'" class="email-progress">
              <el-progress 
                :percentage="getEmailProgress()" 
                :status="getEmailProgress() === 100 ? 'success' : null"
                :format="formatEmailProgress"
              />
            </div>

            <!-- 日志 -->
            <div v-if="emailLogs.length" class="email-logs">
              <div class="logs-title">处理日志</div>
              <div class="logs-content">
                <div v-for="(log, idx) in recentEmailLogs" :key="`log-${idx}`" :class="emailLogClass(log)">{{ log }}</div>
              </div>
            </div>

            <div v-if="recentEmailErrors.length" class="email-logs email-errors">
              <div class="logs-title">错误信息</div>
              <div class="logs-content">
                <div v-for="(err, idx) in recentEmailErrors" :key="`err-${idx}`" class="log-item error">{{ err }}</div>
              </div>
            </div>

            <div v-if="!emailTask || emailTask.status === 'not_found'" class="email-empty">
              尚未启动邮箱拉取任务，填写邮箱信息后点击“开始拉取”。
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <div class="quick-actions">
        <el-button type="primary" :loading="recognizeSubmitting" @click="startRecognizeUnrecognized()">开始识别</el-button>
        <el-button icon="el-icon-refresh" @click="manualRefresh">刷新</el-button>
        <el-button type="warning" :disabled="!selectedRows.length" :loading="retryingRows" @click="retrySelected">重试选中</el-button>
        <el-button type="danger" icon="el-icon-delete" :loading="clearing" @click="confirmClearAll">清空历史</el-button>
        <span class="hint-text">邮箱拉取会自动刷新进度；识别任务可手动点击“刷新”查看最新状态</span>
      </div>
    </el-card>

    <task-progress-panel
      v-if="showRecognizeTaskPanel && recognizeTask && recognizeTask.status !== 'not_found'"
      :task="recognizeTask"
      title="当前识别任务"
      @close="showRecognizeTaskPanel = false"
    />
    <task-progress-panel
      v-if="showEmailTaskPanel && emailTask && emailTask.status !== 'not_found'"
      :task="emailTask"
      title="当前邮箱任务"
      @close="handleEmailTaskPanelClose"
    />

    <el-card class="operation-card" shadow="never">
      <div class="operation-bottom">
        <el-select v-model="filters.recognitionStatus" clearable placeholder="按识别状态筛选" size="small" style="width: 160px">
          <el-option label="处理中" :value="0" />
          <el-option label="识别成功" :value="1" />
          <el-option label="识别失败" :value="2" />
        </el-select>

        <el-select v-model="filters.batchId" clearable filterable placeholder="按批次筛选" size="small" style="width: 220px">
          <el-option v-for="b in batches" :key="b.id" :label="`${b.id}（${batchStatusLabel(b.status)}）`" :value="b.id" />
        </el-select>

        <el-date-picker
          v-model="filters.dateRange"
          type="daterange"
          unlink-panels
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          size="small"
          value-format="yyyy-MM-dd"
        />

        <el-input
          v-model="filters.keyword"
          clearable
          size="small"
          style="width: 260px"
          placeholder="搜索文件名 / 发票号 / 购买方 / 销售方"
          @keyup.enter.native="loadInvoiceList(true)"
        >
          <el-button slot="append" icon="el-icon-search" @click="loadInvoiceList(true)">查询</el-button>
        </el-input>
      </div>

      <div v-if="pendingFiles.length" class="pending-files">
        <div class="pending-title">待上传文件（{{ pendingFiles.length }}）</div>
        <div class="pending-list">
          <el-tag v-for="(f, idx) in pendingFiles" :key="`${f.name}-${idx}`" closable @close="removePendingFile(idx)">
            {{ f.name }}
          </el-tag>
        </div>
      </div>
    </el-card>

    <el-card class="table-card" shadow="never">
      <div class="table-header">
        <div class="left">历史任务清单</div>
        <div class="right">共 {{ invoicePagination.total }} 条</div>
      </div>

      <el-table
        :data="invoiceList"
        stripe
        border
        size="small"
        v-loading="tableLoading"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="46" />
        <el-table-column type="index" label="序号" width="58" />
        <el-table-column prop="batch_id" label="批次号" width="170" show-overflow-tooltip />
        <el-table-column prop="filename" label="文件名" min-width="180" show-overflow-tooltip />
        <el-table-column prop="invoice_number" label="发票号码" width="180" show-overflow-tooltip />
        <el-table-column prop="buyer" label="购买方" min-width="160" show-overflow-tooltip />
        <el-table-column prop="seller" label="销售方" min-width="160" show-overflow-tooltip />
        <el-table-column label="价税合计" width="120" align="right">
          <template slot-scope="scope">{{ money(scope.row.total_with_tax || scope.row.invoice_amount) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template slot-scope="scope">
            <el-tag size="mini" :type="runtimeStatusMeta(scope.row).type">{{ runtimeStatusMeta(scope.row).label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="总耗时" width="110" align="right">
          <template slot-scope="scope">{{ duration(scope.row.total_duration_ms) }}</template>
        </el-table-column>
        <el-table-column label="更新时间" width="168" show-overflow-tooltip>
          <template slot-scope="scope">{{ datetime(scope.row.updated_at || scope.row.upload_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="210" fixed="right">
          <template slot-scope="scope">
            <el-button type="text" @click="openDetail(scope.row)">查看详情</el-button>
            <el-button type="text" @click="retryInvoice(scope.row)">重试</el-button>
            <el-button type="text" class="danger-text" @click="deleteInvoice(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="table-empty" v-if="!tableLoading && !invoiceList.length">
        {{ emptyText }}
      </div>

      <div class="pagination-wrap">
        <el-pagination
          background
          layout="total, prev, pager, next, jumper"
          :current-page.sync="invoicePagination.page"
          :page-size="invoicePagination.limit"
          :total="invoicePagination.total"
          @current-change="onPageChange"
        />
      </div>
    </el-card>

    <invoice-detail-dialog
      :visible.sync="detailVisible"
      :invoice="currentInvoice"
      :steps="currentSteps"
      :loading="detailLoading"
    />
  </div>
</template>

<script>
import { workbenchAPI } from '@/api/workbench'
import InvoiceDetailDialog from '@/components/InvoiceDetailDialog.vue'
import TaskProgressPanel from '@/components/TaskProgressPanel.vue'
import {
  INVOICE_RUNTIME_STATUS,
  BATCH_STATUS,
  EMAIL_STAGE,
} from '@/constants/workbench'

export default {
  name: 'InvoiceWorkbench',
  components: { InvoiceDetailDialog, TaskProgressPanel },
  data() {
    return {
      userId: '',
      activeTab: 'upload',
      overview: {
        total_batches: 0,
        total_invoices: 0,
        processing_count: 0,
        success_count: 0,
        failed_count: 0,
        today_new: 0,
        avg_duration_ms: 0,
      },
      batches: [],
      invoiceList: [],
      selectedRows: [],
      pendingFiles: [],
      dragOver: false,
      uploading: false,
      tableLoading: false,
      clearing: false,
      retryingRows: false,
      emailSubmitting: false,
      recognizeSubmitting: false,
      detailVisible: false,
      detailLoading: false,
      currentInvoice: {},
      currentSteps: [],
      filters: {
        recognitionStatus: undefined,
        batchId: '',
        dateRange: [],
        keyword: '',
      },
      invoicePagination: {
        page: 1,
        limit: 20,
        total: 0,
      },
      emailForm: {
        mailbox: '',
        authCode: '',
        rangeKey: '3m',
        customDateRange: [],
      },
      emailStats: {
        scanned_emails: 0,
        matched_emails: 0,
        downloaded_attachments: 0,
        imported_invoices: 0,
        recognized_invoices: 0,
        failed_count: 0,
      },
      emailLogs: [],
      emailErrors: [],
      emailPollingTimer: null,
      emailPollingJobId: '',
      emailPollingInFlight: false,

      recognizeTask: null,
      emailTask: null,
      showRecognizeTaskPanel: true,
      showEmailTaskPanel: true,
    }
  },
  computed: {
    overviewCards() {
      return [
        { key: 'batches', label: '总批次数', value: this.overview.total_batches, icon: 'el-icon-collection-tag' },
        { key: 'invoices', label: '总发票数', value: this.overview.total_invoices, icon: 'el-icon-tickets' },
        { key: 'processing', label: '处理中', value: this.overview.processing_count, icon: 'el-icon-loading' },
        { key: 'success', label: '成功数量', value: this.overview.success_count, icon: 'el-icon-circle-check' },
        { key: 'failed', label: '失败数量', value: this.overview.failed_count, icon: 'el-icon-warning-outline' },
        { key: 'today', label: '今日新增', value: this.overview.today_new, icon: 'el-icon-date' },
        { key: 'avg', label: '平均耗时', value: this.duration(this.overview.avg_duration_ms), icon: 'el-icon-timer' },
      ]
    },
    emptyText() {
      if (this.filters.keyword || this.filters.batchId || this.filters.recognitionStatus !== undefined || (this.filters.dateRange || []).length) {
        return '当前筛选条件下没有匹配结果'
      }
      return '暂无发票记录，请先上传发票开始处理'
    },
    emailStageLabel() {
      const stage = this.emailTask?.current_stage || ''
      return EMAIL_STAGE[stage] || stage || '未开始'
    },
    recentEmailLogs() {
      return (this.emailLogs || []).slice(-20).reverse()
    },
    recentEmailErrors() {
      return (this.emailErrors || []).slice(-10).reverse()
    },
  },
  async mounted() {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    this.userId = user.id || ''
    if (!this.userId) {
      this.$message.error('请先登录后使用发票工作台')
      this.$router.push('/login')
      return
    }
    await this.loadAll()
  },
  beforeDestroy() {
    this.stopEmailTaskPolling()
  },
  methods: {
    runtimeStatusMeta(row) {
      const runtime = row?.runtime_status || this.mapLegacyStatus(row?.recognition_status)
      return INVOICE_RUNTIME_STATUS[runtime] || { label: '未知', type: 'info' }
    },
    mapLegacyStatus(recognitionStatus) {
      if (recognitionStatus === 1) return 'completed'
      if (recognitionStatus === 2) return 'failed'
      return 'pending'
    },
    batchStatusLabel(status) {
      return (BATCH_STATUS[status] || { label: status || '-' }).label
    },
    money(v) {
      if (v === undefined || v === null || v === '') return '-'
      return `￥${Number(v).toFixed(2)}`
    },
    duration(ms) {
      if (!ms) return '-'
      if (ms < 1000) return `${Number(ms).toFixed(0)} ms`
      return `${(Number(ms) / 1000).toFixed(2)} s`
    },
    datetime(val) {
      if (!val) return '-'
      return String(val).replace('T', ' ').slice(0, 19)
    },
    buildInvoiceQueryParams() {
      const [dateFrom, dateTo] = this.filters.dateRange || []
      return {
        page: this.invoicePagination.page,
        limit: this.invoicePagination.limit,
        keyword: this.filters.keyword || undefined,
        batch_id: this.filters.batchId || undefined,
        recognition_status: this.filters.recognitionStatus,
        date_from: dateFrom || undefined,
        date_to: dateTo ? `${dateTo}T23:59:59` : undefined,
      }
    },
    async loadAll(resetPage = false) {
      await Promise.all([this.loadOverview(), this.loadBatches(), this.loadInvoiceList(resetPage), this.loadLatestTasks()])
    },
    async manualRefresh() {
      await this.loadAll(false)
    },
    async loadLatestTasks() {
      try {
        const [recognizeLatest, emailLatest] = await Promise.all([
          workbenchAPI.getLatestRecognizeTask(this.userId),
          workbenchAPI.getLatestEmailPushTask(this.userId),
        ])

        if (recognizeLatest && recognizeLatest.status && recognizeLatest.status !== 'not_found') {
          this.recognizeTask = recognizeLatest
          this.showRecognizeTaskPanel = true
        } else {
          this.recognizeTask = null
        }

        if (emailLatest && emailLatest.status && emailLatest.status !== 'not_found') {
          this.applyEmailTask(emailLatest)
          this.showEmailTaskPanel = true
          if (this.isEmailTaskRunning(emailLatest.status)) {
            this.startEmailTaskPolling(emailLatest.job_id)
          }
        } else {
          this.emailTask = null
          this.emailStats = {
            scanned_emails: 0,
            matched_emails: 0,
            downloaded_attachments: 0,
            imported_invoices: 0,
            recognized_invoices: 0,
            failed_count: 0,
          }
          this.emailLogs = []
          this.emailErrors = []
          this.stopEmailTaskPolling()
        }
      } catch (_) {
        this.recognizeTask = null
        this.emailTask = null
        this.stopEmailTaskPolling()
      }
    },

    async loadOverview() {
      try {
        this.overview = await workbenchAPI.getOverview(this.userId)
      } catch (e) {
        this.$message.error(`获取总览失败：${e.message}`)
      }
    },

    async loadBatches() {
      try {
        const data = await workbenchAPI.getBatches(this.userId, { page: 1, limit: 100 })
        this.batches = data.batches || []
      } catch (e) {
        this.$message.error(`获取批次失败：${e.message}`)
      }
    },

    async loadInvoiceList(resetPage = false, silent = false) {
      if (resetPage) this.invoicePagination.page = 1
      if (!silent) this.tableLoading = true
      try {
        const data = await workbenchAPI.getInvoices(this.userId, this.buildInvoiceQueryParams())
        this.invoiceList = data.invoices || []
        this.invoicePagination.total = data.total || 0
        if (data.task_summary && data.task_summary.status !== 'not_found') {
          this.recognizeTask = data.task_summary
        }
      } catch (e) {
        this.$message.error(`获取历史清单失败：${e.message}`)
      } finally {
        if (!silent) this.tableLoading = false
      }
    },

    onPageChange(page) {
      this.invoicePagination.page = page
      this.loadInvoiceList(false)
    },

    onSelectionChange(rows) {
      this.selectedRows = rows
    },

    onChooseFiles(e) {
      const files = Array.from(e.target.files || [])
      this.pendingFiles.push(...files.map((f) => ({ name: f.name, raw: f })))
      e.target.value = ''
    },

    onDropFiles(e) {
      this.dragOver = false
      const files = Array.from(e.dataTransfer.files || [])
      this.pendingFiles.push(...files.map((f) => ({ name: f.name, raw: f })))
    },

    removePendingFile(index) {
      this.pendingFiles.splice(index, 1)
    },

    async submitBatchUpload() {
      if (!this.pendingFiles.length) {
        this.$message.warning('请先选择文件')
        return
      }
      this.uploading = true
      try {
        const result = await workbenchAPI.submitInvoices(this.pendingFiles, '', this.userId)
        const createdCount = Number(result?.created_count || (result?.created_invoices || []).length || 0)
        const failedCount = Number(result?.failed_count || (result?.failed_files || []).length || 0)
        if (createdCount > 0) {
          this.$message.success(`上传成功，已生成 ${createdCount} 条待识别记录`)
        }
        if (failedCount > 0) {
          const firstError = result?.failed_files?.[0]?.error_message || '部分文件处理失败'
          this.$message.warning(`有 ${failedCount} 个文件上传失败：${firstError}`)
        }
        this.pendingFiles = []
        await this.loadAll(false)
      } catch (e) {
        this.$message.error(`上传失败：${e.message}`)
      } finally {
        this.uploading = false
      }
    },

    async openDetail(row) {
      this.detailVisible = true
      this.detailLoading = true
      try {
        const invoiceId = row.invoice_id || row.id
        const [invoice, steps] = await Promise.all([
          workbenchAPI.getInvoiceDetail(this.userId, invoiceId),
          workbenchAPI.getInvoiceSteps(this.userId, invoiceId),
        ])
        this.currentInvoice = invoice || {}
        this.currentSteps = steps || []
      } catch (e) {
        this.$message.error(`加载详情失败：${e.message}`)
      } finally {
        this.detailLoading = false
      }
    },

    async retryInvoice(row) {
      try {
        await this.$confirm('确定重新执行该发票识别流程吗？', '确认重试', { type: 'warning' })
        const invoiceId = row.invoice_id || row.id
        await workbenchAPI.retryInvoice(this.userId, invoiceId)
        this.$message.success('已提交重试任务，请手动点击“刷新”查看状态')
      } catch (e) {
        if (e !== 'cancel') {
          this.$message.error(`重试失败：${e.message || e}`)
        }
      }
    },

    async retrySelected() {
      if (!this.selectedRows.length) {
        this.$message.warning('请先选择需要重试的记录')
        return
      }
      try {
        await this.$confirm(`确定重试选中的 ${this.selectedRows.length} 条发票吗？`, '批量重试', { type: 'warning' })
        this.retryingRows = true
        for (const row of this.selectedRows) {
          const invoiceId = row.invoice_id || row.id
          await workbenchAPI.retryInvoice(this.userId, invoiceId)
        }
        this.$message.success('批量重试任务已提交，请手动点击“刷新”查看状态')
      } catch (e) {
        if (e !== 'cancel') {
          this.$message.error(`批量重试失败：${e.message || e}`)
        }
      } finally {
        this.retryingRows = false
      }
    },

    async deleteInvoice(row) {
      try {
        await this.$confirm('删除后将同时清理该发票步骤调试数据，是否继续？', '确认删除', { type: 'warning' })
        const invoiceId = row.invoice_id || row.id
        await workbenchAPI.deleteInvoice(this.userId, invoiceId)
        this.$message.success('删除成功')
        await this.loadAll(false)
      } catch (e) {
        if (e !== 'cancel') {
          this.$message.error(`删除失败：${e.message || e}`)
        }
      }
    },

    async confirmClearAll() {
      try {
        await this.$confirm(
          '该操作将删除全部批次、发票记录、步骤调试 JSON 和预处理产物，且不可恢复。是否继续？',
          '确认清空历史',
          {
            type: 'warning',
            confirmButtonText: '确认清空',
            cancelButtonText: '取消',
          },
        )
        this.clearing = true
        await workbenchAPI.clearAllHistory(this.userId)
        this.$message.success('历史记录已清空')
        await this.loadAll(false)
      } catch (e) {
        if (e !== 'cancel') {
          this.$message.error(`清空失败：${e.message || e}`)
        }
      } finally {
        this.clearing = false
      }
    },

    applyEmailTask(task) {
      this.emailTask = task || null
      this.emailStats = {
        scanned_emails: Number(task?.scanned_emails || task?.total_messages || 0),
        matched_emails: Number(task?.matched_emails || task?.matched_messages || 0),
        downloaded_attachments: Number(task?.downloaded_attachments || task?.downloaded || 0),
        imported_invoices: Number(task?.imported_invoices || task?.imported || task?.completed || 0),
        recognized_invoices: Number(task?.recognized_invoices || 0),
        failed_count: Number(task?.failed_count || task?.failed || 0),
      }
      this.emailLogs = Array.isArray(task?.logs) ? task.logs : []
      this.emailErrors = Array.isArray(task?.errors) ? task.errors : []
    },
    isEmailTaskRunning(status) {
      return ['queued', 'running'].includes(status)
    },
    emailTaskStatusLabel(status) {
      const labelMap = {
        queued: '排队中',
        running: '处理中',
        completed: '已完成',
        failed: '失败',
        partial_success: '部分成功',
        cancelled: '已取消',
        not_found: '任务不存在',
      }
      return labelMap[status] || status || '-'
    },
    isEmailTaskTerminal(status) {
      return ['completed', 'failed', 'partial_success', 'cancelled'].includes(status)
    },
    handleEmailTaskPanelClose() {
      this.showEmailTaskPanel = false
      this.stopEmailTaskPolling()
    },
    startEmailTaskPolling(jobId) {
      if (!jobId) return
      if (this.emailPollingTimer && this.emailPollingJobId === jobId) return
      this.stopEmailTaskPolling()
      this.emailPollingJobId = jobId
      this.pollEmailTaskStatus(jobId)
      this.emailPollingTimer = setInterval(() => {
        this.pollEmailTaskStatus(jobId)
      }, 1500)
    },
    stopEmailTaskPolling() {
      if (this.emailPollingTimer) {
        clearInterval(this.emailPollingTimer)
        this.emailPollingTimer = null
      }
      this.emailPollingJobId = ''
      this.emailPollingInFlight = false
    },
    async pollEmailTaskStatus(jobId) {
      if (!jobId || this.emailPollingInFlight) return
      this.emailPollingInFlight = true
      try {
        const task = await workbenchAPI.getEmailPushTaskStatus(jobId, this.userId)
        if (!task || task.status === 'not_found') {
          this.stopEmailTaskPolling()
          return
        }
        this.applyEmailTask(task)
        this.showEmailTaskPanel = true
        await this.loadOverview()
        await this.loadInvoiceList(false, true)
        if (this.isEmailTaskTerminal(task.status)) {
          await Promise.all([this.loadBatches(), this.loadInvoiceList(false, true)])
          this.stopEmailTaskPolling()
          if (task.status === 'completed') {
            if (Number(task.matched_emails || 0) === 0) {
              this.$message.info('未找到符合条件的邮件，已结束本次拉取')
            } else {
              this.$message.success('邮箱拉取完成，清单已自动刷新')
            }
          } else if (task.status === 'partial_success') {
            this.$message.warning('邮箱拉取部分成功，请查看日志与错误信息')
          } else if (task.status === 'failed') {
            this.$message.error('邮箱拉取失败，请查看错误信息')
          }
        }
      } catch (_) {
        // 轮询失败时保持静默，下一个周期继续尝试
      } finally {
        this.emailPollingInFlight = false
      }
    },
    // 邮箱拉取
    async startEmailPush() {
      const { mailbox, authCode, rangeKey, customDateRange } = this.emailForm
      if (!authCode) {
        this.$message.warning('请填写授权码')
        return
      }
      const [startDate, endDate] = customDateRange || []

      this.emailSubmitting = true
      this.emailLogs = []
      this.emailErrors = []
      this.applyEmailTask({
        task_type: 'email_pull',
        status: 'queued',
        current_stage: 'queued',
        logs: ['任务创建中...'],
      })

      try {
        const task = await workbenchAPI.startEmailPushTask(this.userId, {
          rangeKey,
          mailbox,
          authCode,
          startDate,
          endDate,
        })
        this.applyEmailTask(task)
        this.showEmailTaskPanel = true
        this.startEmailTaskPolling(task.job_id)
        this.$message.success('邮箱任务进行中，正在搜索指定日期范围内的邮件')
      } catch (e) {
        this.$message.error(`启动邮箱拉取失败：${e.message}`)
      } finally {
        this.emailSubmitting = false
      }
    },

    formatEmailProgress(percentage) {
      if (percentage === 100) return '完成'
      return `${percentage}%`
    },
    getEmailProgress() {
      const val = Number(this.emailTask?.progress_percent || 0)
      if (Number.isNaN(val)) return 0
      return Math.max(0, Math.min(100, Math.round(val)))
    },
    emailLogClass(log) {
      const text = String(log || '')
      if (text.includes('错误') || text.includes('失败')) return 'log-item error'
      return 'log-item'
    },

    // 识别任务
    async startRecognizeUnrecognized(batchId = '') {
      try {
        const task = await workbenchAPI.recognizeUnrecognized(this.userId, batchId)
        this.recognizeTask = task
        this.showRecognizeTaskPanel = true
        this.$message.success('已提交识别任务，请稍后点击“刷新”查看最新状态')
      } catch (e) {
        if (e.message && (e.message.includes('没有待识别') || e.message.includes('未识别'))) {
          this.$message.info('没有待识别的发票')
        } else {
          this.$message.error(`启动识别失败：${e.message}`)
        }
      }
    },
  },
}
</script>

<style scoped lang="scss">
$primary: #4f46e5;
$primary-light: #818cf8;
$accent: #06b6d4;

.workbench-page {
  --wb-primary: #{$primary};
  --wb-primary-soft: #eef0ff;
  --wb-text-main: #1e293b;
  --wb-text-sub: #64748b;
  --wb-border: #e2e8f0;
  --wb-bg: #f8fafc;
  --wb-card: rgba(255, 255, 255, 0.85);

  position: relative;
  padding: 18px;
  background: radial-gradient(1200px 500px at 0% -20%, rgba($primary-light, 0.12) 0%, transparent 48%),
    radial-gradient(1200px 500px at 100% -20%, rgba($accent, 0.1) 0%, transparent 46%),
    var(--wb-bg);
  min-height: calc(100vh - 84px);
  animation: wb-fade-in 0.45s ease-out;
}

.workbench-page::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.45), rgba(255, 255, 255, 0));
  pointer-events: none;
}

.workbench-header {
  margin-bottom: 14px;
  position: relative;
  z-index: 1;
  .title {
    font-size: 28px;
    font-weight: 700;
    color: var(--wb-text-main);
    letter-spacing: -0.5px;
    margin: 0;
  }
  .desc {
    margin-top: 6px;
    color: var(--wb-text-sub);
    font-size: 14px;
  }
}

.overview-row {
  margin-bottom: 14px;
  position: relative;
  z-index: 1;
}

.overview-card {
  border-radius: 16px;
  border: 1px solid rgba(79, 70, 229, 0.08);
  backdrop-filter: blur(8px);
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.92));
  box-shadow: 0 8px 24px rgba(79, 70, 229, 0.06);
  transition: transform 0.2s ease, box-shadow 0.24s ease, border-color 0.24s ease;
  animation: wb-rise 0.42s ease both;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 14px 28px rgba(79, 70, 229, 0.12);
    border-color: rgba(79, 70, 229, 0.18);
  }

  .card-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .card-label {
    color: var(--wb-text-sub);
    font-size: 12px;
    letter-spacing: 0.2px;
  }

  .card-icon {
    width: 26px;
    height: 26px;
    border-radius: 8px;
    background: var(--wb-primary-soft);
    color: var(--wb-primary);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
  }

  .card-value {
    margin-top: 8px;
    font-size: 24px;
    font-weight: 700;
    color: var(--wb-text-main);
    letter-spacing: 0.2px;
  }
}

.operation-card,
.table-card {
  border-radius: 16px;
  margin-bottom: 14px;
  border: 1px solid rgba(79, 70, 229, 0.06);
  box-shadow: 0 8px 24px rgba(79, 70, 229, 0.05);
  background: var(--wb-card);
  backdrop-filter: blur(12px);
  position: relative;
  z-index: 1;
}

.operation-top {
  display: flex;
  gap: 12px;
  align-items: stretch;
  margin-bottom: 12px;
}

.upload-area {
  flex: 1;
  border: 1px dashed rgba($primary, 0.25);
  border-radius: 14px;
  padding: 14px;
  background: linear-gradient(135deg, #fafaff 0%, #f5f3ff 100%);
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;

  &.dragover {
    border-color: var(--wb-primary);
    background: #eef0ff;
    transform: translateY(-1px);
  }
}

.hidden-input {
  display: none;
}

.upload-text {
  .main {
    color: #303133;
    font-size: 13px;
    margin-bottom: 4px;
  }
  .sub {
    color: #909399;
    font-size: 12px;
  }
}

.upload-actions {
  margin-top: 12px;
  display: flex;
  gap: 10px;
}

.quick-actions {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  flex-wrap: wrap;
  margin-top:20px;
  :deep(.el-button) {
    border-radius: 10px;
    transition: all 0.18s ease;
  }

  :deep(.el-button--primary) {
    border-color: $primary;
    background: linear-gradient(135deg, $primary, $primary-light);
    box-shadow: 0 8px 18px rgba($primary, 0.24);
  }

  :deep(.el-button--primary:hover) {
    transform: translateY(-1px);
    box-shadow: 0 12px 24px rgba($primary, 0.3);
  }

  :deep(.el-button--warning) {
    background: linear-gradient(135deg, #f59e0b, #d97706);
    border-color: #d97706;
    color: #fff;
  }

  :deep(.el-button--danger) {
    background: linear-gradient(135deg, #ef4444, #dc2626);
    border-color: #dc2626;
  }
}

.hint-text {
  font-size: 12px;
  color: var(--wb-text-sub);
  line-height: 32px;
}

.upload-tabs {
  ::v-deep .el-tabs__header {
    margin-bottom: 16px;
  }
}

.email-panel {
  padding: 14px;
}

.email-form {
  margin-bottom: 14px;
}

.email-stats {
  margin-top: 14px;
  margin-bottom: 14px;

  .stat-card {
    background: linear-gradient(160deg, #fafaff 0%, #f0eeff 100%);
    border: 1px solid rgba($primary, 0.1);
    border-radius: 14px;
    padding: 14px 10px;
    text-align: center;
    transition: transform 0.18s ease, box-shadow 0.22s ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 10px 20px rgba($primary, 0.1);
    }

    .stat-label {
      font-size: 12px;
      color: var(--wb-text-sub);
      margin-bottom: 8px;
    }

    .stat-value {
      font-size: 22px;
      font-weight: 600;
      color: var(--wb-text-main);

      &.success {
        color: #67c23a;
      }

      &.error {
        color: #f56c6c;
      }
    }
  }
}

.email-progress {
  margin: 14px 0;

  :deep(.el-progress-bar__outer) {
    background-color: #ededff;
    height: 10px !important;
    border-radius: 999px;
  }

  :deep(.el-progress-bar__inner) {
    background: linear-gradient(90deg, $primary, $primary-light);
    border-radius: 999px;
    transition: width 0.35s ease;
  }
}

.email-stage-card {
  margin: 12px 0;
  padding: 12px 14px;
  border: 1px solid rgba($primary, 0.12);
  border-radius: 14px;
  background: linear-gradient(160deg, #fafaff 0%, #f5f3ff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
  animation: wb-fade-in 0.25s ease-out;
}

.stage-line {
  font-size: 12px;
  color: #3f4d60;
  line-height: 1.8;
}

.email-logs {
  margin-top: 12px;
  border: 1px solid rgba($primary, 0.1);
  border-radius: 12px;
  background: #fafaff;
  max-height: 300px;
  overflow-y: auto;

  .logs-title {
    font-size: 12px;
    font-weight: 600;
    color: #4f5b72;
    padding: 9px 12px;
    border-bottom: 1px solid rgba($primary, 0.06);
    background: #f5f3ff;
  }

  .logs-content {
    padding: 8px 12px;

    .log-item {
      font-size: 12px;
      color: #45556e;
      line-height: 1.7;
      padding: 4px 0;
      animation: wb-fade-in 0.2s ease-out;
    }

    .log-item.error {
      color: #f56c6c;
      font-weight: 500;
    }
  }
}

.email-errors {
  border-color: #fde2e2;
  background: #fff8f8;
}

.email-empty {
  margin-top: 12px;
  color: var(--wb-text-sub);
  font-size: 12px;
  background: #fafaff;
  border: 1px dashed rgba($primary, 0.18);
  padding: 10px 12px;
  border-radius: 12px;
}

.ocr-progress-alert {
  margin-bottom: 12px;
  
  .ocr-progress-content {
    padding: 8px 0;
    
    .el-progress {
      margin-bottom: 8px;
    }
    
    .ocr-logs {
      margin-top: 8px;
      max-height: 120px;
      overflow-y: auto;
      background: rgba(245, 247, 250, 0.5);
      border-radius: 4px;
      padding: 8px 12px;
      
      .ocr-log-item {
        font-size: 12px;
        color: #606266;
        line-height: 1.6;
        padding: 2px 0;
      }
    }
  }
}

.operation-bottom {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.pending-files {
  margin-top: 12px;
}

.pending-title {
  font-size: 12px;
  color: #606266;
  margin-bottom: 6px;
}

.pending-list {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;

  :deep(.el-tag) {
    border-radius: 999px;
    background: #f0eeff;
    border: 1px solid rgba($primary, 0.15);
    color: $primary;
  }
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  .left {
    font-size: 16px;
    font-weight: 600;
    color: var(--wb-text-main);
  }
  .right {
    font-size: 12px;
    color: var(--wb-text-sub);
  }
}

.danger-text {
  color: #f56c6c;
}

.table-empty {
  padding: 28px 24px;
  text-align: center;
  color: var(--wb-text-sub);
  font-size: 13px;
  background: #fafaff;
  border: 1px dashed rgba($primary, 0.15);
  border-radius: 12px;
}

.pagination-wrap {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}

:deep(.el-table) {
  border-radius: 12px;
  overflow: hidden;
}

:deep(.el-table th.el-table__cell) {
  background: #f8f7ff;
  color: #4a4563;
  font-weight: 600;
  border-bottom: 1px solid rgba($primary, 0.08);
}

:deep(.el-table .cell) {
  line-height: 1.5;
}

:deep(.el-table tr) {
  transition: background-color 0.16s ease;
}

:deep(.el-table--striped .el-table__body tr.el-table__row--striped td) {
  background: #fcfbff;
}

:deep(.el-table__body tr:hover > td) {
  background-color: #f5f3ff !important;
}

:deep(.el-tag) {
  border-radius: 999px;
  border: 0;
}

:deep(.el-tabs__item) {
  transition: all 0.2s ease;
}

:deep(.el-tabs__item:hover) {
  color: var(--wb-primary);
}

:deep(.el-tabs__item.is-active) {
  color: var(--wb-primary);
  font-weight: 600;
}

@media (max-width: 1200px) {
  .overview-row :deep(.el-col) {
    width: 25%;
    margin-bottom: 10px;
  }

  .operation-top {
    flex-direction: column;
  }

  .quick-actions {
    width: 100%;
  }
}

@media (max-width: 768px) {
  .overview-row :deep(.el-col) {
    width: 50%;
  }
}

@keyframes wb-fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes wb-rise {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
