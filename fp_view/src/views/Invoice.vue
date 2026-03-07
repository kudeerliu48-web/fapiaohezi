<template>
  <div class="workbench-page">
    <div class="workbench-header">
      <h1 class="title">发票调试工作台</h1>
      <p class="desc">面向发票识别链路调试、历史追踪与批次运营</p>
    </div>

    <el-row :gutter="12" class="overview-row">
      <el-col :span="3" v-for="card in overviewCards" :key="card.key">
        <el-card shadow="hover" class="overview-card">
          <div class="card-label">{{ card.label }}</div>
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
                <el-form-item>
                  <el-button type="primary" :loading="emailSubmitting" @click="startEmailPush">开始拉取</el-button>
                </el-form-item>
              </el-form>
            </div>

            <!-- 统计卡片 -->
            <div v-if="emailTask && emailTask.status !== 'not_found'" class="email-stats">
              <el-row :gutter="12">
                <el-col :span="6">
                  <div class="stat-card">
                    <div class="stat-label">匹配邮件数</div>
                    <div class="stat-value">{{ emailStats.matched_messages }}</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-card">
                    <div class="stat-label">已下载附件</div>
                    <div class="stat-value">{{ emailStats.downloaded }}</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-card">
                    <div class="stat-label">已成功导入</div>
                    <div class="stat-value success">{{ emailStats.imported }}</div>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-card">
                    <div class="stat-label">失败数量</div>
                    <div class="stat-value error">{{ emailStats.failed }}</div>
                  </div>
                </el-col>
              </el-row>
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
                <div v-for="(log, idx) in emailLogs" :key="idx" class="log-item">{{ log }}</div>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>

      <div class="quick-actions">
        <el-button type="primary" :loading="recognizeSubmitting" @click="startRecognizeUnrecognized()">开始识别</el-button>
        <el-button icon="el-icon-refresh" @click="manualRefresh">刷新</el-button>
        <el-button type="warning" :disabled="!selectedRows.length" :loading="retryingRows" @click="retrySelected">重试选中</el-button>
        <el-button type="danger" icon="el-icon-delete" :loading="clearing" @click="confirmClearAll">清空历史</el-button>
        <span class="hint-text">任务提交后请手动点击“刷新”查看最新状态</span>
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
      @close="showEmailTaskPanel = false"
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
      },
      emailStats: {
        matched_messages: 0,
        downloaded: 0,
        imported: 0,
        failed: 0,
      },
      emailLogs: [],

      recognizeTask: null,
      emailTask: null,
      showRecognizeTaskPanel: true,
      showEmailTaskPanel: true,
    }
  },
  computed: {
    overviewCards() {
      return [
        { key: 'batches', label: '总批次数', value: this.overview.total_batches },
        { key: 'invoices', label: '总发票数', value: this.overview.total_invoices },
        { key: 'processing', label: '处理中', value: this.overview.processing_count },
        { key: 'success', label: '成功数量', value: this.overview.success_count },
        { key: 'failed', label: '失败数量', value: this.overview.failed_count },
        { key: 'today', label: '今日新增', value: this.overview.today_new },
        { key: 'avg', label: '平均耗时', value: this.duration(this.overview.avg_duration_ms) },
      ]
    },
    emptyText() {
      if (this.filters.keyword || this.filters.batchId || this.filters.recognitionStatus !== undefined || (this.filters.dateRange || []).length) {
        return '当前筛选条件下没有匹配结果'
      }
      return '暂无发票记录，请先上传发票开始处理'
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
          this.emailTask = emailLatest
          this.showEmailTaskPanel = true
          this.emailStats = {
            matched_messages: emailLatest.matched_messages || 0,
            downloaded: emailLatest.downloaded || 0,
            imported: emailLatest.completed || emailLatest.imported || 0,
            failed: emailLatest.failed || 0,
          }
          this.emailLogs = emailLatest.logs || []
        } else {
          this.emailTask = null
          this.emailStats = { matched_messages: 0, downloaded: 0, imported: 0, failed: 0 }
          this.emailLogs = []
        }
      } catch (_) {
        this.recognizeTask = null
        this.emailTask = null
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

    async loadInvoiceList(resetPage = false) {
      if (resetPage) this.invoicePagination.page = 1
      this.tableLoading = true
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
        this.tableLoading = false
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
        const result = await workbenchAPI.uploadBatch(this.userId, this.pendingFiles)
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

    // 邮箱拉取
    async startEmailPush() {
      const { mailbox, authCode, rangeKey } = this.emailForm
      if (!mailbox || !authCode) {
        this.$message.warning('请填写邮箱地址和授权码')
        return
      }

      this.emailSubmitting = true
      this.emailStats = { matched_messages: 0, downloaded: 0, imported: 0, failed: 0 }
      this.emailLogs = []

      try {
        const task = await workbenchAPI.startEmailPushTask(this.userId, { rangeKey, mailbox, authCode })
        this.emailTask = task
        this.showEmailTaskPanel = true
        this.emailStats = {
          matched_messages: task.matched_messages || 0,
          downloaded: task.downloaded || 0,
          imported: task.completed || task.imported || 0,
          failed: task.failed || 0,
        }
        this.emailLogs = task.logs || []
        this.$message.success('邮箱拉取任务已提交，请稍后点击“刷新”查看最新结果')
      } catch (e) {
        this.$message.error(`启动邮箱推送失败：${e.message}`)
      } finally {
        this.emailSubmitting = false
      }
    },

    formatEmailProgress(percentage) {
      if (percentage === 100) {
        return '完成'
      }
      return `${percentage}%`
    },
    getEmailProgress() {
      if (this.emailTask && this.emailTask.progress_percent !== undefined) {
        return Math.round(Number(this.emailTask.progress_percent || 0))
      }
      if (!this.emailStats.matched_messages) return 0
      return Math.floor((this.emailStats.downloaded / this.emailStats.matched_messages) * 100)
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
.workbench-page {
  padding: 16px;
  background: #f5f7fa;
  min-height: calc(100vh - 84px);
}

.workbench-header {
  margin-bottom: 12px;
  .title {
    font-size: 24px;
    color: #303133;
    margin: 0;
  }
  .desc {
    margin-top: 6px;
    color: #909399;
    font-size: 13px;
  }
}

.overview-row {
  margin-bottom: 12px;
}

.overview-card {
  border-radius: 10px;
  .card-label {
    color: #909399;
    font-size: 12px;
  }
  .card-value {
    margin-top: 8px;
    font-size: 20px;
    font-weight: 600;
    color: #303133;
  }
}

.operation-card,
.table-card {
  border-radius: 10px;
  margin-bottom: 12px;
}

.operation-top {
  display: flex;
  gap: 12px;
  align-items: stretch;
  margin-bottom: 12px;
}

.upload-area {
  flex: 1;
  border: 1px dashed #c0c4cc;
  border-radius: 8px;
  padding: 12px;
  background: #fafcff;
  &.dragover {
    border-color: #409eff;
    background: #ecf5ff;
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
  margin-top: 10px;
  display: flex;
  gap: 8px;
}

.quick-actions {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.hint-text {
  font-size: 12px;
  color: #909399;
  line-height: 32px;
}

.upload-tabs {
  ::v-deep .el-tabs__header {
    margin-bottom: 16px;
  }
}

.email-panel {
  padding: 12px;
}

.email-form {
  margin-bottom: 16px;
}

.email-stats {
  margin-top: 16px;
  margin-bottom: 16px;
  
  .stat-card {
    background: #f5f7fa;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
    
    .stat-label {
      font-size: 13px;
      color: #909399;
      margin-bottom: 8px;
    }
    
    .stat-value {
      font-size: 24px;
      font-weight: 600;
      color: #303133;
      
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
  margin: 16px 0;
}

.email-logs {
  margin-top: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fafafa;
  max-height: 300px;
  overflow-y: auto;
  
  .logs-title {
    font-size: 13px;
    font-weight: 600;
    color: #606266;
    padding: 10px 12px;
    border-bottom: 1px solid #e4e7ed;
    background: #f5f7fa;
  }
  
  .logs-content {
    padding: 8px 12px;
    
    .log-item {
      font-size: 12px;
      color: #606266;
      line-height: 1.8;
      padding: 4px 0;
    }
  }
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
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.pending-files {
  margin-top: 10px;
}

.pending-title {
  font-size: 12px;
  color: #606266;
  margin-bottom: 6px;
}

.pending-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  .left {
    font-size: 15px;
    font-weight: 600;
    color: #303133;
  }
  .right {
    font-size: 12px;
    color: #909399;
  }
}

.danger-text {
  color: #f56c6c;
}

.table-empty {
  padding: 24px;
  text-align: center;
  color: #909399;
  font-size: 13px;
}

.pagination-wrap {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 1200px) {
  .overview-row :deep(.el-col) {
    width: 25%;
    margin-bottom: 8px;
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
</style>

