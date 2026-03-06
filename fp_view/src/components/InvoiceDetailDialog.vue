<template>
  <el-dialog
    :visible.sync="dialogVisible"
    title="发票处理详情"
    width="92%"
    top="4vh"
    class="invoice-detail-dialog"
    :close-on-click-modal="false"
  >
    <div v-loading="loading" class="detail-layout">
      <div class="preview-pane">
        <div class="pane-header">
          <span>发票预览</span>
          <div class="preview-tools">
            <el-radio-group v-model="previewMode" size="mini">
              <el-radio-button label="processed">预处理图</el-radio-button>
              <el-radio-button label="original">原图</el-radio-button>
            </el-radio-group>
            <el-button size="mini" @click="zoomOut">-</el-button>
            <el-button size="mini" @click="fitImage">适配</el-button>
            <el-button size="mini" @click="zoomIn">+</el-button>
          </div>
        </div>
        <div class="preview-meta">
          <span>文件名：{{ invoice.filename || '-' }}</span>
          <span>页码：{{ invoice.page_index || 1 }}</span>
          <span>大小：{{ formatSize(invoice.file_size) }}</span>
        </div>
        <div class="image-container" @wheel.prevent="onWheel">
          <img
            v-if="currentImage"
            :src="currentImage"
            :style="{ transform: `scale(${zoom})` }"
            class="invoice-image"
            alt="发票预览"
          />
          <div v-else class="empty-preview">暂无可预览图片</div>
        </div>
      </div>

      <div class="pipeline-pane">
        <div class="summary-card">
          <div class="summary-title">最终结构化结果</div>
          <div class="summary-grid">
            <div class="summary-item"><label>发票号码</label><span>{{ invoice.invoice_number || '-' }}</span></div>
            <div class="summary-item"><label>发票日期</label><span>{{ invoice.invoice_date || '-' }}</span></div>
            <div class="summary-item"><label>购买方</label><span>{{ invoice.buyer || '-' }}</span></div>
            <div class="summary-item"><label>销售方</label><span>{{ invoice.seller || '-' }}</span></div>
            <div class="summary-item"><label>服务/货物</label><span>{{ invoice.service_name || '-' }}</span></div>
            <div class="summary-item"><label>金额</label><span>{{ formatMoney(invoice.amount_without_tax) }}</span></div>
            <div class="summary-item"><label>税额</label><span>{{ formatMoney(invoice.tax_amount) }}</span></div>
            <div class="summary-item"><label>价税合计</label><span>{{ formatMoney(invoice.total_with_tax || invoice.invoice_amount) }}</span></div>
          </div>
        </div>

        <div class="steps-panel">
          <div class="steps-title">处理步骤调试</div>
          <el-collapse v-model="activeSteps">
            <el-collapse-item
              v-for="step in normalizedSteps"
              :key="step.step_name"
              :name="step.step_name"
            >
              <template slot="title">
                <div class="step-title-row">
                  <span>{{ step.label }}</span>
                  <el-tag size="mini" :type="step.statusType">{{ step.statusLabel }}</el-tag>
                  <span class="step-duration">{{ step.durationLabel }}</span>
                </div>
              </template>
              <div class="step-meta">
                <div>开始时间：{{ step.started_at || '-' }}</div>
                <div>结束时间：{{ step.ended_at || '-' }}</div>
                <div v-if="step.error_message" class="step-error">错误信息：{{ step.error_message }}</div>
              </div>
              <div class="step-json-block">
                <json-viewer title="输入 payload" :value="step.input_payload" />
                <json-viewer title="输出 payload" :value="step.output_payload" />
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>
    </div>
  </el-dialog>
</template>

<script>
import JsonViewer from '@/components/JsonViewer.vue'
import { STEP_META, STEP_STATUS } from '@/constants/workbench'

export default {
  name: 'InvoiceDetailDialog',
  components: { JsonViewer },
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
    invoice: {
      type: Object,
      default: () => ({}),
    },
    steps: {
      type: Array,
      default: () => [],
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      previewMode: 'processed',
      zoom: 1,
      activeSteps: ['preprocess'],
    }
  },
  computed: {
    dialogVisible: {
      get() {
        return this.visible
      },
      set(v) {
        this.$emit('update:visible', v)
      },
    },
    currentImage() {
      const processed = this.toAbsoluteUrl(this.invoice.processed_file_path || this.invoice.processed_filename, 'processed')
      const original = this.toAbsoluteUrl(this.invoice.original_file_path || this.invoice.saved_filename, 'uploads')
      return this.previewMode === 'original' ? (original || processed) : (processed || original)
    },
    normalizedSteps() {
      return [...this.steps]
        .sort((a, b) => (a.step_order || 99) - (b.step_order || 99))
        .map((s) => {
          const meta = STEP_META[s.step_name] || { label: s.step_name, order: 99 }
          const statusMeta = STEP_STATUS[s.status] || { label: s.status || '-', type: 'info' }
          return {
            ...s,
            label: meta.label,
            statusLabel: statusMeta.label,
            statusType: statusMeta.type,
            durationLabel: s.duration_ms ? `${Number(s.duration_ms).toFixed(0)} ms` : '-',
          }
        })
    },
  },
  watch: {
    visible(val) {
      if (val) {
        this.previewMode = 'processed'
        this.zoom = 1
      }
    },
    steps: {
      handler(newVal) {
        if (newVal?.length) {
          this.activeSteps = [newVal[0].step_name]
        }
      },
      immediate: true,
    },
  },
  methods: {
    toAbsoluteUrl(value, folder) {
      if (!value) return ''
      if (String(value).startsWith('http')) return value
      if (String(value).startsWith('/files/')) {
        return `http://localhost:8000${value}`
      }
      if (folder && this.invoice?.id) {
        const user = JSON.parse(localStorage.getItem('user') || '{}')
        if (user.id) {
          return `http://localhost:8000/files/${user.id}/${folder}/${encodeURIComponent(value)}`
        }
      }
      return ''
    },
    zoomIn() {
      this.zoom = Math.min(3, +(this.zoom + 0.1).toFixed(1))
    },
    zoomOut() {
      this.zoom = Math.max(0.2, +(this.zoom - 0.1).toFixed(1))
    },
    fitImage() {
      this.zoom = 1
    },
    onWheel(e) {
      if (e.deltaY < 0) {
        this.zoomIn()
      } else {
        this.zoomOut()
      }
    },
    formatMoney(v) {
      if (v === undefined || v === null || v === '') return '-'
      return `￥${Number(v).toFixed(2)}`
    },
    formatSize(bytes) {
      if (!bytes) return '-'
      if (bytes < 1024) return `${bytes} B`
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
      return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
    },
  },
}
</script>

<style scoped lang="scss">
.detail-layout {
  display: flex;
  gap: 16px;
  min-height: 72vh;
}

.preview-pane,
.pipeline-pane {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 12px;
}

.preview-pane {
  flex: 1.1;
  display: flex;
  flex-direction: column;
}

.pipeline-pane {
  flex: 1.4;
  overflow: auto;
}

.pane-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.preview-meta {
  display: flex;
  gap: 12px;
  color: #909399;
  font-size: 12px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.image-container {
  flex: 1;
  border: 1px solid #f0f2f5;
  border-radius: 8px;
  background: #f8fafc;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: auto;
}

.invoice-image {
  max-width: 100%;
  max-height: 100%;
  transform-origin: center center;
  transition: transform .1s ease-in-out;
}

.empty-preview {
  color: #909399;
}

.summary-card {
  margin-bottom: 14px;
  padding: 10px;
  border-radius: 8px;
  background: #f8fbff;
  border: 1px solid #e6eef8;
}

.summary-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 12px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  label {
    color: #909399;
    flex-shrink: 0;
  }
  span {
    color: #303133;
    text-align: right;
    word-break: break-all;
  }
}

.steps-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}

.step-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.step-duration {
  color: #909399;
  font-size: 12px;
}

.step-meta {
  font-size: 12px;
  color: #606266;
  margin-bottom: 8px;
}

.step-error {
  color: #f56c6c;
}

.step-json-block {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

@media (max-width: 1200px) {
  .detail-layout {
    flex-direction: column;
  }
}
</style>

