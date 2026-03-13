<template>
  <div class="workbench-page">
    <div class="workbench-header">
      <h1 class="title">发票工作台</h1>
      <p class="desc">上传发票文件，提交识别，查看结果</p>
    </div>

    <el-card class="operation-card" shadow="never">
      <el-tabs v-model="activeTab" class="upload-tabs">
        <!-- 图片上传 Tab -->
        <el-tab-pane label="图片上传" name="upload">
          <UploadAndBatches
            v-if="userId"
            :user-id="userId"
            :can-recognize="quotaInfo.canRecognize"
            :quota-message="quotaInfo.quotaMessage"
            :invoice-list="invoiceList"
            :batches="batches"
            @refresh="loadInvoiceList"
          />
        </el-tab-pane>

        <!-- 邮箱拉取 Tab -->
        <el-tab-pane label="邮箱拉取" name="email">
          <EmailPull
            v-if="userId"
            :user-id="userId"
            :can-recognize="quotaInfo.canRecognize"
            :quota-message="quotaInfo.quotaMessage"
            @refresh="loadInvoiceList"
          />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <InvoiceList
      v-if="userId"
      :user-id="userId"
      :can-recognize="quotaInfo.canRecognize"
      :quota-message="quotaInfo.quotaMessage"
      :invoice-list="invoiceList"
      :loading="tableLoading"
      @refresh="loadInvoiceList"
      @filter-change="onInvoiceFilterChange"
    />
  </div>
</template>

<script>
import authAPI from '@/api/auth'
import workbenchAPI from '@/api/workbench'
import UploadAndBatches from '@/views/invoice/UploadAndBatches.vue'
import EmailPull from '@/views/invoice/EmailPull.vue'
import InvoiceList from '@/views/invoice/InvoiceList.vue'

export default {
  name: 'InvoiceWorkbench',
  components: { UploadAndBatches, EmailPull, InvoiceList },
  data() {
    return {
      userId: '',
      activeTab: 'upload',
      tableLoading: false,
      batches: [],
      invoiceList: [],
      quotaInfo: {
        canRecognize: true,
        quotaMessage: '',
      },
      invoiceFilters: {
        recognizeRange: [],
      },
    }
  },
  async mounted() {
    const user = JSON.parse(localStorage.getItem('user') || '{}')
    this.userId = user.id || ''
    if (!this.userId) {
      this.$message.error('请先登录')
      this.$router.push('/login')
      return
    }
    await this.loadQuotaInfo()
    await this.loadInvoiceList()
    await this.loadBatches()
  },
  methods: {
    datetime(val) {
      if (!val) return '-'
      return String(val).replace('T', ' ').slice(0, 16)
    },
    async loadQuotaInfo() {
      try {
        const res = await authAPI.getUserInfo(this.userId)
        const data = res?.data?.data || res?.data || {}
        this.quotaInfo = {
          canRecognize: data.can_recognize !== false,
          quotaMessage: data.quota_message || '',
        }
      } catch (e) {
        this.quotaInfo = { canRecognize: true, quotaMessage: '' }
      }
    },
    // 获取批次列表
    async loadBatches() {
      const batchMap = new Map()
      this.invoiceList.forEach(inv => {
        if (!batchMap.has(inv.batch_id)) {
          batchMap.set(inv.batch_id, {
            batch_id: inv.batch_id,
            total_files: 0,
            status: 'pending',
            success_count: 0,
            failed_count: 0,
            pending_count: 0,
            avg_duration_ms: 0,
            _duration_sum: 0,
            _duration_cnt: 0,
          })
        }
        const b = batchMap.get(inv.batch_id)
        b.total_files++
        if (inv.recognition_status === 1) b.success_count++
        else if (inv.recognition_status === 2) b.failed_count++
        else b.pending_count++

        const d = Number(inv.total_duration_ms || 0)
        if (d && !Number.isNaN(d) && d > 0) {
          b._duration_sum += d
          b._duration_cnt += 1
        }
      })
      this.batches = Array.from(batchMap.values()).map((b) => {
        const avg = b._duration_cnt ? b._duration_sum / b._duration_cnt : 0
        const status = b.pending_count > 0 ? 'pending' : (b.failed_count > 0 ? 'completed' : 'completed')
        return {
          batch_id: b.batch_id,
          total_files: b.total_files,
          status,
          success_count: b.success_count,
          failed_count: b.failed_count,
          pending_count: b.pending_count,
          avg_duration_ms: avg,
        }
      })
    },

    // 获取发票列表
    async loadInvoiceList() {
      this.tableLoading = true
      try {
        const params = { page: 1, limit: 100 }
        const range = this.invoiceFilters.recognizeRange || []
        if (range && range.length === 2) {
          const [start, end] = range
          params.recognize_date_from = this.datetime(start)
          params.recognize_date_to = this.datetime(end)
        }

        const data = await workbenchAPI.getInvoices(this.userId, params)
        this.invoiceList = data?.invoices || []
        await this.loadBatches()
        await this.loadQuotaInfo()
      } catch (e) {
        this.$message.error(`获取发票列表失败：${e.message}`)
      } finally {
        this.tableLoading = false
      }
    },

    onInvoiceFilterChange(payload) {
      this.invoiceFilters = { ...this.invoiceFilters, ...(payload || {}) }
      this.loadInvoiceList()
    },
  }
}
</script>

<style scoped lang="scss">
$primary: #4f46e5;
$primary-light: #818cf8;

.workbench-page {
  padding: 18px;
  background: #f8fafc;
  min-height: calc(100vh - 84px);
}

.workbench-header {
  margin-bottom: 14px;
  .title {
    font-size: 28px;
    font-weight: 700;
    color: #1e293b;
    margin: 0;
  }
  .desc {
    margin-top: 6px;
    color: #64748b;
    font-size: 14px;
  }
}

.operation-card,
.table-card {
  border-radius: 16px;
  margin-bottom: 14px;
}

/* 统一按钮风格（圆角/高度/宽度） */
::deep(.ui-btn.el-button) {
  height: 34px;
  min-width: 86px;
  padding: 0 14px;
  border-radius: 12px;
  font-weight: 600;
}

::deep(.ui-btn--primary.el-button) {
  background: linear-gradient(90deg, $primary, $primary-light);
  border: none;
}

::deep(.ui-btn--danger.el-button) {
  background: #b91c1c; /* 深红 */
  border-color: #b91c1c;
  color: #fff;
}

::deep(.ui-btn--danger.el-button:hover),
::deep(.ui-btn--danger.el-button:focus) {
  background: #991b1b;
  border-color: #991b1b;
}

::deep(.ui-btn.el-button.is-text) {
  height: auto;
  min-width: auto;
  padding: 0;
}

/* 图标按钮（用于详情/重试/删除） */
::deep(.ui-icon-btn.el-button) {
  height: 34px;
  width: 34px;
  min-width: 34px;
  padding: 0;
  border-radius: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

::deep(.ui-icon-btn.el-button .el-icon-view),
::deep(.ui-icon-btn.el-button .el-icon-refresh),
::deep(.ui-icon-btn.el-button .el-icon-delete) {
  font-size: 16px;
}

::deep(.ui-icon-btn.el-button) {
  background: #ffffff;
  border: 1px solid rgba(15, 23, 42, 0.12);
  color: #0f172a;
}

::deep(.ui-icon-btn.el-button:hover) {
  border-color: rgba(79, 70, 229, 0.35);
  color: $primary;
}

::deep(.ui-icon-btn--primary.el-button) {
  background: linear-gradient(90deg, $primary, $primary-light);
  border: none;
  color: #fff;
}

::deep(.ui-icon-btn--danger.el-button) {
  background: #b91c1c;
  border-color: #b91c1c;
  color: #fff;
}

::deep(.ui-icon-btn--danger.el-button:hover),
::deep(.ui-icon-btn--danger.el-button:focus) {
  background: #991b1b;
  border-color: #991b1b;
  color: #fff;
}

// 邮箱拉取样式
.email-panel {
  padding: 10px;
}

.email-stats {
  margin-top: 20px;

  .stat-card {
    background: #f8fafc;
    border-radius: 8px;
    padding: 12px;
    text-align: center;

    .stat-label {
      font-size: 12px;
      color: #64748b;
      margin-bottom: 4px;
    }

    .stat-value {
      font-size: 18px;
      font-weight: 600;
      color: #1e293b;

      &.error {
        color: #f56c6c;
      }
    }
  }
}

.email-status {
  margin-top: 16px;
  padding: 12px;
  background: #f0f9ff;
  border-radius: 8px;
  font-size: 14px;
  color: #0369a1;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  .left {
    font-size: 16px;
    font-weight: 600;
    color: #1e293b;
  }
}

.table-empty {
  padding: 40px;
  text-align: center;
  color: #909399;
}

// 发票详情弹框样式
.invoice-detail {
  .detail-section {
    margin-bottom: 24px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  .detail-title {
    font-size: 14px;
    font-weight: 600;
    color: #1e293b;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid #e2e8f0;
  }

  .detail-item {
    margin-bottom: 10px;
    font-size: 13px;

    .label {
      color: #64748b;
    }
  }

  .attachment-preview {
    background: #f8fafc;
    border-radius: 8px;
    padding: 20px;
    text-align: center;

    .preview-image {
      max-width: 100%;
      max-height: 400px;
      border-radius: 4px;
    }

    .file-preview {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;

      i {
        font-size: 48px;
        color: #94a3b8;
      }

      span {
        color: #64748b;
        font-size: 14px;
      }
    }
  }

  .error-message {
    color: #f56c6c;
    font-size: 13px;
    padding: 12px;
    background: #fef2f2;
    border-radius: 6px;
  }
}
</style>
