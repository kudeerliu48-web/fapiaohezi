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
      <div class="operation-top">
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

        <div class="quick-actions">
          <el-button icon="el-icon-refresh" @click="loadAll">刷新</el-button>
          <el-button type="warning" :disabled="!selectedRows.length" :loading="retryingRows" @click="retrySelected">重试选中</el-button>
          <el-button type="danger" icon="el-icon-delete" :loading="clearing" @click="confirmClearAll">清空历史</el-button>
        </div>
      </div>

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
            <el-tag size="mini" :type="statusMeta(scope.row.recognition_status).type">{{ statusMeta(scope.row.recognition_status).label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="总耗时" width="110" align="right">
          <template slot-scope="scope">{{ duration(scope.row.total_duration_ms) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" width="168" show-overflow-tooltip>
          <template slot-scope="scope">{{ datetime(scope.row.upload_time) }}</template>
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
import { authAPI } from '@/api/auth'
import { workbenchAPI } from '@/api/workbench'
import InvoiceDetailDialog from '@/components/InvoiceDetailDialog.vue'
import { INVOICE_STATUS, BATCH_STATUS } from '@/constants/workbench'

export default {
  name: 'InvoiceWorkbench',
  components: { InvoiceDetailDialog },
  data() {
    return {
      userId: '',
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
    statusMeta(status) {
      return INVOICE_STATUS[status] || { label: '未知', type: 'info' }
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

    async loadAll() {
      await Promise.all([this.loadOverview(), this.loadBatches(), this.loadInvoiceList(true)])
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
        const [dateFrom, dateTo] = this.filters.dateRange || []
        const data = await workbenchAPI.getInvoices(this.userId, {
          page: this.invoicePagination.page,
          limit: this.invoicePagination.limit,
          keyword: this.filters.keyword || undefined,
          batch_id: this.filters.batchId || undefined,
          recognition_status: this.filters.recognitionStatus,
          date_from: dateFrom || undefined,
          date_to: dateTo ? `${dateTo}T23:59:59` : undefined,
        })
        this.invoiceList = data.invoices || []
        this.invoicePagination.total = data.total || 0
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
        await workbenchAPI.uploadBatch(this.userId, this.pendingFiles)
        this.$message.success('上传成功，批次已创建')
        this.pendingFiles = []
        await this.loadAll()
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
        const [invoice, steps] = await Promise.all([
          workbenchAPI.getInvoiceDetail(this.userId, row.id),
          workbenchAPI.getInvoiceSteps(this.userId, row.id),
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
        await workbenchAPI.retryInvoice(this.userId, row.id)
        this.$message.success('已重新执行识别')
        await this.loadAll()
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
          // 串行执行，避免瞬时并发过高
          await workbenchAPI.retryInvoice(this.userId, row.id)
        }
        this.$message.success('批量重试完成')
        await this.loadAll()
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
        await workbenchAPI.deleteInvoice(this.userId, row.id)
        this.$message.success('删除成功')
        await this.loadAll()
      } catch (e) {
        if (e !== 'cancel') {
          this.$message.error(`删除失败：${e.message || e}`)
        }
      }
    },

    async confirmClearAll() {
      try {
        await this.$confirm(
          '该操作将删除全部批次、发票记录、步骤调试JSON和预处理产物，且不可恢复。是否继续？',
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
        await this.loadAll()
      } catch (e) {
        if (e !== 'cancel') {
          this.$message.error(`清空失败：${e.message || e}`)
        }
      } finally {
        this.clearing = false
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
