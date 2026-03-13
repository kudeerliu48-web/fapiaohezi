<template>
  <div>
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
        <div class="sub">支持 JPG / PNG / PDF，单次可上传多文件</div>
      </div>
      <div class="upload-actions">
        <el-button type="primary" icon="el-icon-upload2" class="ui-btn ui-btn--primary" @click="$refs.uploadInput.click()">选择文件</el-button>
        <el-button class="ui-btn" :disabled="!pendingFiles.length" :loading="uploading" @click="submitBatchUpload">上传并创建批次</el-button>
      </div>

      <div v-if="pendingFiles.length" class="pending-files">
        <div class="pending-title">已选择 {{ pendingFiles.length }} 个文件：</div>
        <div class="file-list">
          <div v-for="(file, index) in pendingFiles" :key="index" class="file-item">
            <span class="file-name">{{ file.name }}</span>
            <i class="el-icon-close" @click="removePendingFile(index)"></i>
          </div>
        </div>
      </div>
    </div>

    <div v-if="batches && batches.length" class="batch-list">
      <div class="batch-header">
        <div class="batch-title">待识别批次</div>
        <div class="batch-actions">
          <el-button
            v-if="pendingBatchIds.length > 0"
            type="primary"
            size="small"
            class="ui-btn ui-btn--primary"
            :loading="recognizingAll"
            :disabled="!canRecognize"
            @click="startRecognizeAll"
          >一键识别 ({{ pendingBatchIds.length }}个批次)</el-button>
          <el-button size="small" type="danger" class="ui-btn ui-btn--danger" @click="clearAllBatches">清除文件</el-button>
        </div>
      </div>

      <el-row :gutter="12" class="batch-overview">
        <el-col :xs="24" :sm="6">
          <div class="overview-card oc-success">
            <div class="oc-label">成功</div>
            <div class="oc-value">{{ overviewComputed.success }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="6">
          <div class="overview-card oc-pending">
            <div class="oc-label">待识别</div>
            <div class="oc-value">{{ overviewComputed.pending }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="6">
          <div class="overview-card oc-fail">
            <div class="oc-label">失败</div>
            <div class="oc-value">{{ overviewComputed.failed }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :sm="6">
          <div class="overview-card oc-time">
            <div class="oc-label">总计</div>
            <div class="oc-value">{{ overviewComputed.total }}</div>
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script>
import api from '@/api/auth'
import config from '@/config'
import workbenchAPI from '@/api/workbench'

export default {
  name: 'UploadAndBatches',
  props: {
    userId: { type: String, required: true },
    canRecognize: { type: Boolean, default: true },
    quotaMessage: { type: String, default: '' },
    invoiceList: { type: Array, default: () => [] },
    batches: { type: Array, default: () => [] },
  },
  data() {
    return {
      pendingFiles: [],
      dragOver: false,
      uploading: false,
      recognizingAll: false,
      streamSources: {},
    }
  },
  beforeDestroy() {
    try {
      Object.values(this.streamSources || {}).forEach((es) => {
        try { es.close() } catch (e) {}
      })
    } catch (e) {}
    this.streamSources = {}
  },
  computed: {
    pendingBatchIds() {
      return (this.batches || []).filter((b) => b.status === 'pending').map((b) => b.batch_id)
    },
    overviewComputed() {
      const invoices = Array.isArray(this.invoiceList) ? this.invoiceList : []
      let success = 0
      let pending = 0
      let failed = 0
      let sum = 0
      let cnt = 0
      for (const inv of invoices) {
        if (inv.recognition_status === 1) success++
        else if (inv.recognition_status === 2) failed++
        else pending++
        const d = Number(inv.total_duration_ms || 0)
        if (d && !Number.isNaN(d) && d > 0) {
          sum += d
          cnt += 1
        }
      }
      return { success, pending, failed, total: success + pending + failed, avg_duration_ms: cnt ? sum / cnt : 0 }
    },
  },
  methods: {
    formatDurationMs(ms) {
      const v = Number(ms)
      if (!v || Number.isNaN(v) || v <= 0) return '-'
      if (v < 1000) return `${Math.round(v)} ms`
      if (v < 60_000) return `${(v / 1000).toFixed(1)} s`
      return `${(v / 60_000).toFixed(1)} min`
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
        this.$message.success('上传成功，已创建批次')
        this.pendingFiles = []
        this.$emit('refresh')
      } catch (e) {
        this.$message.error(`上传失败：${e.message}`)
      } finally {
        this.uploading = false
      }
    },
    async startRecognizeAll() {
      if (this.pendingBatchIds.length === 0) {
        this.$message.warning('没有待识别的批次')
        return
      }
      if (!this.canRecognize && this.quotaMessage) {
        this.$message.warning(this.quotaMessage)
        return
      }
      this._quotaDialogShown = false
      this.recognizingAll = true
      let ok = 0
      let fail = 0
      for (const batchId of this.pendingBatchIds) {
        try {
          const res = await api.post(`/invoices/submit/${this.userId}/${batchId}`, {}, { timeout: 300000 })
          if (res.data?.success) {
            ok++
            this.pollBatchStatus(batchId)
          } else {
            fail++
            const data = res.data || {}
            const code = data.code
            const msg = data.message || ''
            const isQuotaError = code === 403 || (msg && (msg.includes('识别次数已用完') || msg.includes('会员已到期')))
            if (isQuotaError) {
              this.showQuotaExhaustedDialog()
            }
          }
        } catch (e) {
          fail++
          const code = e.response?.data?.code
          const msg = e.response?.data?.message || e.message
          const isQuotaError = e.response?.status === 403 || code === 403 || (msg && (msg.includes('识别次数已用完') || msg.includes('会员已到期')))
          if (isQuotaError) {
            this.showQuotaExhaustedDialog()
          } else if (msg) {
            this.$message.error(msg)
          }
        }
      }
      if (ok) this.$message.success(`已提交 ${ok} 个批次进行识别`)
      if (fail && !this._quotaDialogShown) this.$message.error(`${fail} 个批次提交失败`)
      this._quotaDialogShown = false
      this.recognizingAll = false
      this.$emit('refresh')
    },
    showQuotaExhaustedDialog() {
      this._quotaDialogShown = true
      this.$alert('您的识别额度已用完，请前往充值或升级会员后继续使用。', '额度已用完', {
        confirmButtonText: '前往充值',
        type: 'warning',
        callback: () => {
          if (this.$router) this.$router.push('/recharge')
        }
      })
    },
    pollBatchStatus(batchId) {
      if (!batchId) return
      if (this.streamSources[batchId]) return

      const url = `${config.API_PREFIX}/invoices/batches/${batchId}/stream?user_id=${encodeURIComponent(this.userId)}`
      const eventSource = new EventSource(url)
      this.$set(this.streamSources, batchId, eventSource)

      eventSource.addEventListener('invoice_item', (event) => {
        try {
          const item = JSON.parse(event.data)
          this.$emit('stream-item', { batchId, item })
        } catch (e) {}
      })

      eventSource.addEventListener('batch_done', (event) => {
        try {
          const done = JSON.parse(event.data)
          this.$emit('batch-done', { batchId, done })
        } catch (e) {}
        try { eventSource.close() } catch (e) {}
        this.$delete(this.streamSources, batchId)
        this.$emit('refresh')
      })

      eventSource.onerror = () => {
        try { eventSource.close() } catch (e) {}
        this.$delete(this.streamSources, batchId)
        // 留给外层刷新/用户手动刷新；避免无限重连打爆服务
      }
    },
    async clearAllBatches() {
      if (!this.batches.length) {
        this.$message.info('没有可清除的文件')
        return
      }
      try {
        await this.$confirm('确定清除所有批次文件吗？此操作不可恢复。', '清除文件', { type: 'warning' })
        for (const b of this.batches) {
          try {
            await api.delete(`/invoices/batch/${this.userId}/${b.batch_id}`)
          } catch (e) {}
        }
        this.$message.success('已清除')
        this.$emit('refresh')
      } catch (e) {
        if (e !== 'cancel') this.$message.error(`清除失败：${e.message}`)
      }
    },
  },
}
</script>

<style scoped lang="scss">
$primary: #4f46e5;
$primary-light: #818cf8;

.upload-area {
  border: 2px dashed rgba($primary, 0.25);
  border-radius: 14px;
  padding: 40px;
  background: linear-gradient(135deg, #fafaff 0%, #f5f3ff 100%);
  text-align: center;
  transition: all 0.2s ease;

  &.dragover {
    border-color: $primary;
    background: #eef0ff;
  }
}

.hidden-input {
  display: none;
}

.upload-text {
  margin-bottom: 20px;
  .main {
    color: #303133;
    font-size: 16px;
    margin-bottom: 8px;
  }
  .sub {
    color: #909399;
    font-size: 13px;
  }
}

.upload-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.pending-files {
  margin-top: 20px;
  text-align: left;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;

  .pending-title {
    font-size: 13px;
    color: #64748b;
    margin-bottom: 8px;
  }

  .file-list {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .file-item {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 12px;
    background: #f1f5f9;
    border-radius: 6px;
    font-size: 13px;
    .file-name {
      color: #1e293b;
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .el-icon-close {
      color: #94a3b8;
      cursor: pointer;
      font-size: 12px;
      &:hover {
        color: #f56c6c;
      }
    }
  }
}

.batch-list {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e2e8f0;
}

.batch-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.batch-title {
  font-size: 14px;
  font-weight: 600;
  color: #1e293b;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.batch-overview {
  margin-top: 10px;
  margin-bottom: 12px;
}

.overview-card {
  border-radius: 16px;
  padding: 14px 16px;
  border: 1px solid rgba($primary, 0.1);
  box-shadow: 0 10px 24px rgba($primary, 0.08);
  background: linear-gradient(135deg, #ffffff, #fafaff);
  margin-bottom: 12px;
  .oc-label {
    font-size: 12px;
    color: #64748b;
    margin-bottom: 8px;
  }
  .oc-value {
    font-size: 24px;
    font-weight: 800;
    color: #0f172a;
    line-height: 1;
  }
  &.oc-success {
    background: linear-gradient(135deg, #ecfdf5, #f0fdf4);
    border-color: rgba(34, 197, 94, 0.22);
  }
  &.oc-pending {
    background: linear-gradient(135deg, #fff7ed, #fffbeb);
    border-color: rgba(245, 158, 11, 0.25);
  }
  &.oc-fail {
    background: linear-gradient(135deg, #fef2f2, #fff1f2);
    border-color: rgba(239, 68, 68, 0.22);
  }
  &.oc-time {
    background: linear-gradient(135deg, #eef2ff, #f5f3ff);
    border-color: rgba(79, 70, 229, 0.18);
  }
}
</style>

