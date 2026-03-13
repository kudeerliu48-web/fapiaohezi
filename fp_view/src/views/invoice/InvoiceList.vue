<template>
  <div class="invoice-list-container">
    <el-dialog title="发票完整信息" :visible.sync="detailVisible" width="960px" append-to-body custom-class="fp-dialog fp-dialog--wide">
      <div v-if="currentInvoice" class="invoice-detail">
        <div class="detail-section detail-section--no-title">
          <el-row :gutter="20" class="detail-row-nowrap">
            <el-col :span="12"><div class="detail-item"><span class="label">发票号码：</span>{{ currentInvoice.invoice_number || '' }}</div></el-col>
            <el-col :span="12"><div class="detail-item"><span class="label">开票日期：</span>{{ currentInvoice.invoice_date || '' }}</div></el-col>
            <el-col :span="12"><div class="detail-item"><span class="label">购买方：</span>{{ currentInvoice.buyer || '' }}</div></el-col>
            <el-col :span="12"><div class="detail-item"><span class="label">销售方：</span>{{ currentInvoice.seller || '' }}</div></el-col>
            <el-col :span="12"><div class="detail-item"><span class="label">服务名称：</span>{{ currentInvoice.service_name || '' }}</div></el-col>
            <el-col :span="12"><div class="detail-item"><span class="label">不含税额：</span>{{ detailMoney(currentInvoice.amount_without_tax) }}</div></el-col>
            <el-col :span="12"><div class="detail-item"><span class="label">税额：</span>{{ detailMoney(currentInvoice.tax_amount) }}</div></el-col>
            <el-col :span="12"><div class="detail-item"><span class="label">价税合计：</span>{{ detailMoney(currentInvoice.total_with_tax) }}</div></el-col>
            <el-col :span="24"><div class="detail-item"><span class="label">备注：</span>{{ currentInvoice.field1 || '' }}</div></el-col>
          </el-row>
        </div>
        <div class="detail-section">
          <div class="detail-title">原始文件预览</div>
          <div class="attachment-preview">
            <img v-if="isImage(currentInvoice.saved_filename)" :src="fileUrl(currentInvoice)" class="preview-image" />
            <iframe
              v-else-if="isPdf(currentInvoice.saved_filename) && fileUrl(currentInvoice)"
              :src="pdfPreviewUrl(currentInvoice)"
              class="preview-iframe"
              title="PDF 预览"
            />
            <div v-else class="file-preview-fallback">
              <template v-if="fileUrl(currentInvoice)">
                <p class="fallback-tip">该类型文件在页面内预览受限，可在新窗口中查看：</p>
                <el-button type="text" class="link-open-file" @click="openFile(currentInvoice)">在新窗口打开</el-button>
              </template>
              <p v-else class="fallback-tip">暂无文件路径</p>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 基于当前行新增一条 / 编辑新增行：表单弹框，发票号不可改，其余可编辑 -->
    <el-dialog
      :title="isDeriveEditMode ? '编辑新增行' : '基于当前行新增一条'"
      :visible.sync="deriveVisible"
      width="560px"
      append-to-body
      custom-class="fp-dialog"
      @close="closeDerive"
    >
      <el-form v-if="deriveForm" ref="deriveFormRef" :model="deriveForm" label-width="100px" size="small" class="derive-form">
        <el-form-item label="发票号码">
          <el-input v-model="deriveForm.invoice_number" disabled />
        </el-form-item>
        <el-form-item label="开票日期">
          <el-input v-model="deriveForm.invoice_date" placeholder="开票日期" />
        </el-form-item>
        <el-form-item label="服务名称">
          <el-input v-model="deriveForm.service_name" placeholder="服务名称" />
        </el-form-item>
        <el-form-item label="不含税额">
          <el-input v-model="deriveForm.amount_without_tax" placeholder="不含税额" type="number" />
        </el-form-item>
        <el-form-item label="税额">
          <el-input v-model="deriveForm.tax_amount" placeholder="税额" type="number" />
        </el-form-item>
        <el-form-item label="价税合计">
          <el-input v-model="deriveForm.total_with_tax" placeholder="价税合计" type="number" />
        </el-form-item>
        <el-form-item label="购买方">
          <el-input v-model="deriveForm.buyer" placeholder="购买方" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="销售方">
          <el-input v-model="deriveForm.seller" placeholder="销售方" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="deriveForm.remark" placeholder="备注" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button size="small" class="fp-dialog-btn fp-dialog-btn--cancel" @click="deriveVisible = false">取消</el-button>
        <el-button size="small" type="primary" class="fp-dialog-btn fp-dialog-btn--primary" :loading="deriveSubmitting" @click="submitDerive">
          {{ isDeriveEditMode ? '保存' : '确定新增' }}
        </el-button>
      </span>
    </el-dialog>

    <!-- 仅修改备注弹框（原始数据行） -->
    <el-dialog title="修改备注" :visible.sync="remarkVisible" width="440px" append-to-body custom-class="fp-dialog" @close="remarkRow = null; remarkText = ''">
      <el-input
        v-model="remarkText"
        type="textarea"
        :rows="4"
        placeholder="请输入备注"
                class="fp-dialog-textarea"
      />
      <span slot="footer" class="dialog-footer">
        <el-button size="small" class="fp-dialog-btn fp-dialog-btn--cancel" @click="remarkVisible = false">取消</el-button>
        <el-button size="small" type="primary" class="fp-dialog-btn fp-dialog-btn--primary" :loading="remarkSubmitting" @click="submitRemark">保存</el-button>
      </span>
    </el-dialog>

    <el-card class="table-card" shadow="never">
      <div class="table-header">
        <div class="left">发票工作台 · 发票清单</div>
        <div class="right">
          <el-date-picker
            v-model="filters.recognizeRange"
            type="daterange"
            size="small"
            unlink-panels
            range-separator="至"
            start-placeholder="识别开始日期"
            end-placeholder="识别结束日期"
            style="margin-right: 8px;"
          />
          <el-button size="small" icon="el-icon-search" class="ui-btn ui-btn--refresh" @click="applyFilter">筛选</el-button>
          <el-button size="small" icon="el-icon-download" class="ui-btn ui-btn--export" @click="doExport">导出清单</el-button>
          <el-button size="small" icon="el-icon-refresh" class="ui-btn ui-btn--refresh" @click="$emit('refresh')">刷新列表</el-button>
          <el-button size="small" icon="el-icon-delete" class="ui-btn ui-btn--danger" @click="deleteAll">全部删除</el-button>
        </div>
      </div>

      <el-table 
        :data="invoiceList" 
        stripe 
        border 
        class="invoice-table compact-table" 
        v-loading="loading"
        :header-cell-style="{ background: '#f8fafc', color: '#475569', fontWeight: 'bold' }"
      >
        <el-table-column type="index" label="序号" width="50" align="center" />
        <el-table-column label="状态" width="80" align="center">
          <template slot-scope="scope">
            <span :class="['status-icon', statusIconClass(scope.row.recognition_status)]" :title="statusText(scope.row.recognition_status)">
              <i :class="statusIcon(scope.row.recognition_status)"></i>
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="invoice_number" label="发票号码" width="170" show-overflow-tooltip>
          <template slot-scope="scope">
            <span
              :class="{ 'cell-diff': isCellDiff(scope.row, 'invoice_number') }"
              class="link-invoice-number"
              @click="openDetail(scope.row)"
            >{{ scope.row.invoice_number }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="invoice_date" label="开票日期" width="100" show-overflow-tooltip>
          <template slot-scope="scope">
            <span :class="{ 'cell-diff': isCellDiff(scope.row, 'invoice_date') }">{{ scope.row.invoice_date }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="service_name" label="服务名称" min-width="120" show-overflow-tooltip>
          <template slot-scope="scope">
            <span :class="{ 'cell-diff': isCellDiff(scope.row, 'service_name') }">{{ scope.row.service_name }}</span>
          </template>
        </el-table-column>

        

        <el-table-column label="不含税额" width="100" align="right">
          <template slot-scope="scope">
            <span :class="{ 'cell-diff': isCellDiff(scope.row, 'amount_without_tax') }">{{ money(scope.row.amount_without_tax) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="价税合计" width="100" align="right">
          <template slot-scope="scope">
            <span :class="{ 'cell-diff': isCellDiff(scope.row, 'total_with_tax') }">{{ money(scope.row.total_with_tax) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="buyer" label="购买方" min-width="130" show-overflow-tooltip>
          <template slot-scope="scope">
            <span :class="{ 'cell-diff': isCellDiff(scope.row, 'buyer') }">{{ scope.row.buyer }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="seller" label="销售方" min-width="130" show-overflow-tooltip>
          <template slot-scope="scope">
            <span :class="{ 'cell-diff': isCellDiff(scope.row, 'seller') }">{{ scope.row.seller }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="recognize_time" label="识别日期" width="140" show-overflow-tooltip>
          <template slot-scope="scope">{{ datetime(scope.row.recognize_time) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right" align="center">
          <template slot-scope="scope">
            <el-button type="text" class="op-text-btn op-text-btn--purple" @click="openDetail(scope.row)">查看</el-button>
            <el-button v-if="canDerive(scope.row)" type="text" class="op-text-btn op-text-btn--yellow" @click="openDerive(scope.row)">核对</el-button>
            <el-button v-if="canEditAdded(scope.row)" type="text" class="op-text-btn op-text-btn--yellow" @click="openDerive(scope.row)">修改</el-button>
            <el-button v-if="canEditRemark(scope.row)" type="text" class="op-text-btn op-text-btn--green" @click="openRemark(scope.row)">备注</el-button>
            <el-button v-if="scope.row.recognition_status === 2" type="text" class="op-text-btn op-text-btn--orange" :disabled="!canRecognize" :title="!canRecognize ? quotaMessage : ''" @click="retry(scope.row)">重试</el-button>
            <el-button type="text" class="op-text-btn op-text-btn--red" @click="delOne(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!loading && !invoiceList.length" class="table-empty">
        <i class="el-icon-receiving" style="font-size: 30px; margin-bottom: 10px; display: block;"></i>
        暂无发票记录
      </div>
    </el-card>

    <!-- 导出字段选择弹窗 -->
    <!-- （已按需求去掉字段选择弹窗，导出直接使用当前列表对应的固定字段） -->
  </div>
</template>

<script>
import api from '@/api/auth'
import workbenchAPI from '@/api/workbench'

export default {
  name: 'InvoiceList',
  props: {
    userId: { type: String, required: true },
    canRecognize: { type: Boolean, default: true },
    quotaMessage: { type: String, default: '' },
    invoiceList: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
  },
  data() {
    return {
      detailVisible: false,
      currentInvoice: null,
      deriveVisible: false,
      deriveForm: null,
      deriveSubmitting: false,
      originalDeriveRow: null,
      isDeriveEditMode: false,
      remarkVisible: false,
      remarkRow: null,
      remarkText: '',
      remarkSubmitting: false,
      filters: {
        recognizeRange: [],
      },
    }
  },
  computed: {
    apiBase() {
      return process.env.VUE_APP_BASE_URL || 'http://localhost:8000'
    },
  },
  methods: {
    money(v) {
      if (v === undefined || v === null || v === '') return '-'
      return `${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    },
    /** 弹框内金额：空值不显示横杠 */
    detailMoney(v) {
      if (v === undefined || v === null || v === '') return ''
      return `${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    },
    datetime(val) {
      if (!val) return '-'
      return String(val).replace('T', ' ').slice(0, 16)
    },
    statusIcon(status) {
      if (status === 1) return 'el-icon-success'
      if (status === 2) return 'el-icon-error'
      if (status === 0 || status === null || status === undefined) return 'el-icon-warning'
      return 'el-icon-question'
    },
    statusIconClass(status) {
      if (status === 1) return 'status-icon--success'
      if (status === 2) return 'status-icon--danger'
      if (status === 0 || status === null || status === undefined) return 'status-icon--pending'
      return 'status-icon--unknown'
    },
    statusText(status) {
      if (status === 1) return '成功'
      if (status === 2) return '失败'
      if (status === 0 || status === null || status === undefined) return '待识别'
      return '未知'
    },
    /** 是否可“基于此行新增”：非新增行(非99)，且该行尚未有新增行 */
    canDerive(row) {
      if (!row || row.recognition_status === 99) return false
      const hasAdded = (this.invoiceList || []).some(inv => inv.source_invoice_id === row.id)
      return !hasAdded
    },
    /** 是否可编辑新增行（状态=99） */
    canEditAdded(row) {
      return row && row.recognition_status === 99
    },
    /** 是否可编辑备注（仅原始数据行，非新增行） */
    canEditRemark(row) {
      return row && row.recognition_status !== 99
    },
    /** 新增行对应的原始行 */
    getSourceRow(row) {
      if (!row || row.recognition_status !== 99 || !row.source_invoice_id) return null
      return (this.invoiceList || []).find(inv => inv.id === row.source_invoice_id) || null
    },
    /** 新增行与原始行不同的单元格标黄 */
    isCellDiff(row, field) {
      if (!row || row.recognition_status !== 99) return false
      const src = this.getSourceRow(row)
      if (!src) return false
      const a = row[field]
      const b = src[field]
      if (a === b) return false
      const sa = a === undefined || a === null ? '' : String(a).trim()
      const sb = b === undefined || b === null ? '' : String(b).trim()
      return sa !== sb
    },
    openDerive(row) {
      this.originalDeriveRow = row
      this.isDeriveEditMode = row.recognition_status === 99
      this.deriveForm = {
        invoice_number: row.invoice_number || '',
        invoice_date: row.invoice_date || '',
        service_name: row.service_name || '',
        amount_without_tax: row.amount_without_tax != null ? row.amount_without_tax : '',
        tax_amount: row.tax_amount != null ? row.tax_amount : '',
        total_with_tax: row.total_with_tax != null ? row.total_with_tax : '',
        buyer: row.buyer || '',
        seller: row.seller || '',
        remark: row.field1 || '',
      }
      this.deriveVisible = true
    },
    closeDerive() {
      this.deriveForm = null
      this.originalDeriveRow = null
      this.isDeriveEditMode = false
    },
    openRemark(row) {
      this.remarkRow = row
      this.remarkText = row.field1 || ''
      this.remarkVisible = true
    },
    async submitRemark() {
      if (!this.remarkRow) return
      this.remarkSubmitting = true
      try {
        await workbenchAPI.updateInvoiceRemark(this.userId, this.remarkRow.id, this.remarkText)
        this.$message.success('备注已保存')
        this.remarkVisible = false
        this.remarkRow = null
        this.remarkText = ''
        this.$emit('refresh')
      } catch (e) {
        this.$message.error(e.message || '保存失败')
      } finally {
        this.remarkSubmitting = false
      }
    },
    async submitDerive() {
      if (!this.originalDeriveRow || !this.deriveForm) return
      const body = {
        invoice_date: this.deriveForm.invoice_date || null,
        service_name: this.deriveForm.service_name || null,
        amount_without_tax: this.deriveForm.amount_without_tax !== '' ? Number(this.deriveForm.amount_without_tax) : null,
        tax_amount: this.deriveForm.tax_amount !== '' ? Number(this.deriveForm.tax_amount) : null,
        total_with_tax: this.deriveForm.total_with_tax !== '' ? Number(this.deriveForm.total_with_tax) : null,
        buyer: this.deriveForm.buyer || null,
        seller: this.deriveForm.seller || null,
        remark: this.deriveForm.remark || null,
      }
      this.deriveSubmitting = true
      try {
        if (this.isDeriveEditMode) {
          await workbenchAPI.updateInvoice(this.userId, this.originalDeriveRow.id, body)
          this.$message.success('保存成功')
        } else {
          await workbenchAPI.deriveInvoice(this.userId, this.originalDeriveRow.id, body)
          this.$message.success('新增记录成功')
        }
        this.deriveVisible = false
        this.closeDerive()
        this.$emit('refresh')
      } catch (e) {
        this.$message.error(e.message || (this.isDeriveEditMode ? '保存失败' : '新增失败'))
      } finally {
        this.deriveSubmitting = false
      }
    },
    isImage(filename) {
      if (!filename) return false
      const ext = filename.split('.').pop().toLowerCase()
      return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext)
    },
    isPdf(filename) {
      if (!filename) return false
      return filename.split('.').pop().toLowerCase() === 'pdf'
    },
    /** PDF 预览地址：加 #toolbar=0 隐藏浏览器自带工具栏，只显示内容 */
    pdfPreviewUrl(inv) {
      const url = this.fileUrl(inv)
      if (!url) return ''
      return url + (url.indexOf('#') >= 0 ? '&' : '#') + 'toolbar=0'
    },
    fileUrl(inv) {
      const base = this.apiBase
      const p = inv.processed_file_path || inv.original_file_path
      if (p) return base + (p.startsWith('/') ? p : '/' + p)
      if (inv.saved_filename && this.userId) return `${base}/files/${this.userId}/uploads/${inv.saved_filename}`
      return ''
    },
    openFile(inv) {
      const url = this.fileUrl(inv)
      if (url) window.open(url, '_blank')
    },
    openDetail(row) {
      // 编辑新增行（recognition_status=99）需要沿用原始行的文件信息（同一发票号文件相同）
      if (row && row.recognition_status === 99) {
        const src = this.getSourceRow(row)
        if (src) {
          // 以原始行为基础，叠加新增行的可编辑字段
          this.currentInvoice = {
            ...src,
            invoice_number: row.invoice_number || src.invoice_number,
            invoice_date: row.invoice_date || src.invoice_date,
            service_name: row.service_name || src.service_name,
            amount_without_tax: row.amount_without_tax != null ? row.amount_without_tax : src.amount_without_tax,
            tax_amount: row.tax_amount != null ? row.tax_amount : src.tax_amount,
            total_with_tax: row.total_with_tax != null ? row.total_with_tax : src.total_with_tax,
            buyer: row.buyer || src.buyer,
            seller: row.seller || src.seller,
            field1: row.field1 || src.field1,
            id: row.id, // 保持当前行 id，便于后续操作
          }
          this.detailVisible = true
          return
        }
      }
      this.currentInvoice = { ...row }
      this.detailVisible = true
    },
    async retry(row) {
      if (!this.canRecognize && this.quotaMessage) {
        this.$message.warning(this.quotaMessage)
        return
      }
      try {
        await this.$confirm('确定重新识别该发票吗？', '确认', { type: 'warning', center: true })
        if (!row?.batch_id) return
        const res = await api.post(`/invoices/submit/${this.userId}/${row.batch_id}`, {}, { timeout: 300000 })
        if (!res.data?.success) {
          const data = res.data || {}
          const code = data.code
          const msg = data.message || ''
          const isQuotaError = code === 403 || (msg && (msg.includes('识别次数已用完') || msg.includes('会员已到期')))
          if (isQuotaError) {
            this.showQuotaExhaustedDialog()
          } else {
            this.$message.error(`重试失败：${msg}`)
          }
          return
        }
        this.$message.success('已提交重试')
      } catch (e) {
        if (e !== 'cancel') {
          const code = e.response?.data?.code
          const msg = e.response?.data?.message || e.message
          const isQuotaError = e.response?.status === 403 || code === 403 || (msg && (msg.includes('识别次数已用完') || msg.includes('会员已到期')))
          if (isQuotaError) {
            this.showQuotaExhaustedDialog()
          } else {
            this.$message.error(`重试失败：${msg}`)
          }
        }
      } finally {
        this.$emit('refresh')
      }
    },
    showQuotaExhaustedDialog() {
      this.$alert('您的识别额度已用完，请前往充值或升级会员后继续使用。', '额度已用完', {
        confirmButtonText: '前往充值',
        type: 'warning',
        callback: () => {
          if (this.$router) this.$router.push('/recharge')
        }
      })
    },
    async delOne(row) {
      try {
        await this.$confirm('确定删除该发票吗？', '确认删除', { type: 'error', center: true })
        const res = await api.delete(`/invoices/${this.userId}/${row.id}`)
        if (!res.data?.success) throw new Error(res.data?.message || '删除失败')
        this.$message.success('删除成功')
        this.$emit('refresh')
      } catch (e) {
        if (e !== 'cancel') this.$message.error(`删除失败：${e.message}`)
      }
    },
    async deleteAll() {
      if (!this.invoiceList.length) return this.$message.info('暂无可删除的发票')
      try {
        await this.$confirm('确定清空全部发票吗？此操作不可逆！', '极端危险操作', { 
          confirmButtonText: '确定清空',
          cancelButtonText: '取消',
          type: 'error',
          center: true 
        })
        for (const inv of this.invoiceList) {
          try { await api.delete(`/invoices/${this.userId}/${inv.id}`) } catch (e) {}
        }
        this.$message.success('已清空所有发票记录')
        this.$emit('refresh')
      } catch (e) {
        if (e !== 'cancel') this.$message.error('操作异常')
      }
    },

    applyFilter() {
      this.$emit('filter-change', { recognizeRange: this.filters.recognizeRange || [] })
    },

    async doExport() {
      try {
        const params = { recognition_status: 1 } // 只导出识别成功的
        const range = this.filters.recognizeRange || []
        if (range && range.length === 2) {
          const [start, end] = range
          params.recognize_date_from = this.datetime(start)
          params.recognize_date_to = this.datetime(end)
        }

        const res = await api.get(`/invoices/${this.userId}/export`, {
          params,
          responseType: 'blob',
        })
        const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `发票清单_${this.datetime(new Date()).replace(/[:\s]/g, '-')}.xlsx`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
      } catch (e) {
        this.$message.error(`导出失败：${e.message}`)
      }
    }
  }
}
</script>

<style scoped lang="scss">
// 1. 顶部渐变按钮样式
.ui-btn {
  border: none !important;
  border-radius: 10px !important;
  font-weight: 600 !important;
  color: #ffffff !important;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    opacity: 0.9;
  }

  &--refresh {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important; // 靛蓝紫色
  }

  &--export {
    background: linear-gradient(135deg, #10b981, #059669) !important; // 绿色渐变
  }

  &--danger {
    background: linear-gradient(135deg, #f87171, #ef4444) !important; // 红色渐变
  }
}

// 2. 表格紧凑化美化
.table-card {
  border-radius: 16px;
  border: 1px solid #f1f5f9;
}

.table-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
  .left {
    font-size: 18px;
    font-weight: 700;
    color: #0f172a;
    display: flex;
    align-items: center;
    &::before {
      content: "";
      width: 4px;
      height: 18px;
      background: #6366f1;
      margin-right: 10px;
      border-radius: 4px;
    }
  }
}

// 让日期范围选择器的小号输入框整体下移 2px，使与右侧按钮垂直对齐
.table-header .right {
  display: flex;
  align-items: center;

  ::v-deep .el-range-editor--small.el-input__inner {
    position: relative;
    top: 2px;
  }
}

.compact-table {
  ::v-deep {
    .el-table__cell {
      padding: 8px 0 !important; // 行高增加 4px
      font-size: 13px;
    }
    .cell {
      line-height: 1.4;
      white-space: nowrap;
    }
    .el-table__header th {
      height: 40px;
    }
  }
}

// 状态列图标：成功=绿勾、失败=红叉、待识别=灰叹号、其余=黄问号
.status-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  &--success { color: #10b981; }
  &--danger { color: #ef4444; }
  &--pending { color: #94a3b8; }
  &--unknown { color: #eab308; }
}

// 新增行与原始行不同的单元格：文字为黄色（非背景）
.cell-diff {
  color: #ca8a04 !important;
  font-weight: 500;
}

// 发票号码可点击，打开完整信息弹框
.link-invoice-number {
  cursor: pointer;
  color: #6366f1;
  text-decoration: none;
  &:hover { text-decoration: underline; }
}

// 3. 操作列文字按钮（无边框）：查看紫、新增/修改黄、备注绿、重试橙、删除红
.op-text-btn {
  padding: 0 6px !important;
  margin: 0 2px !important;
  border: none !important;
  font-size: 13px !important;
  min-width: auto !important;
  &--purple { color: #6366f1; }
  &--purple:hover { color: #4f46e5; }
  &--yellow { color: #ca8a04; }
  &--yellow:hover { color: #a16207; }
  &--green { color: #16a34a; }
  &--green:hover { color: #15803d; }
  &--orange { color: #ea580c; }
  &--orange:hover { color: #c2410c; }
  &--red { color: #dc2626; }
  &--red:hover { color: #b91c1c; }
}

// 4. 发票详情弹窗美化
.invoice-detail {
  padding: 0 10px;
  .detail-section {
    margin-bottom: 24px;
    .detail-title {
      font-size: 15px;
      font-weight: 700;
      color: #334155;
      margin-bottom: 15px;
      padding-bottom: 8px;
      border-bottom: 2px solid #f1f5f9;
    }
    &--no-title {
      margin-bottom: 20px;
    }
    .detail-row-nowrap .detail-item {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .detail-item {
      margin-bottom: 12px;
      font-size: 14px;
      color: #1e293b;
      .label { color: #64748b; width: 80px; display: inline-block; }
    }
  }
  .attachment-preview {
    background: #f8fafc;
    border: 2px dashed #e2e8f0;
    border-radius: 12px;
    padding: 24px;
    text-align: center;
    min-height: 320px;
    .preview-image {
      max-width: 100%;
      max-height: 480px;
      border-radius: 8px;
      box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }
    .preview-iframe {
      width: 100%;
      height: 480px;
      border: none;
      border-radius: 8px;
      background: #fff;
    }
    .file-preview-fallback {
      padding: 24px;
      .fallback-tip {
        color: #64748b;
        font-size: 14px;
        margin: 0 0 12px 0;
      }
      .link-open-file {
        color: #6366f1;
        font-size: 14px;
      }
    }
    .file-preview {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 15px;
      i { font-size: 60px; color: #94a3b8; }
    }
  }
}

.table-empty {
  padding: 60px 0;
  text-align: center;
  color: #cbd5e1;
  font-weight: 500;
}

.export-fields {
  .tips {
    font-size: 13px;
    color: #64748b;
    margin-bottom: 6px;
  }
  .field-group {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 10px;
  }
}
</style>

<!-- 弹框统一风格（与主页面按钮/圆角一致，append-to-body 需非 scoped） -->
<style lang="scss">
$fp-primary: #6366f1;
$fp-primary-end: #8b5cf6;
$fp-radius-dialog: 16px;
$fp-radius-btn: 12px;

.fp-dialog.el-dialog {
  border-radius: $fp-radius-dialog;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.15);

  .el-dialog__header {
    background: linear-gradient(135deg, $fp-primary, $fp-primary-end);
    color: #fff;
    padding: 14px 20px;
    border-bottom: none;
    .el-dialog__title {
      color: #fff;
      font-weight: 600;
      font-size: 16px;
    }
    .el-dialog__headerbtn {
      top: 14px;
      width: 32px;
      height: 32px;
      .el-dialog__close {
        color: #fff;
        font-size: 18px;
      }
      &:hover .el-dialog__close {
        color: rgba(255, 255, 255, 0.85);
      }
    }
  }

  .el-dialog__body {
    padding: 20px 24px;
    border-radius: 0 0 $fp-radius-dialog $fp-radius-dialog;
    background: #fff;
  }

  .el-dialog__footer {
    padding: 14px 24px 20px;
    border-top: 1px solid #f1f5f9;
    .dialog-footer {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
    }
  }
}

/* 弹框内按钮：与主页面一致，圆角 12px，主按钮紫色渐变，取消按钮灰边 */
.fp-dialog .fp-dialog-btn.el-button {
  height: 34px;
  min-width: 80px;
  padding: 0 16px;
  border-radius: $fp-radius-btn !important;
  font-weight: 600;
  border: none;
  transition: all 0.2s ease;
}
.fp-dialog .fp-dialog-btn--primary.el-button {
  background: linear-gradient(135deg, $fp-primary, $fp-primary-end) !important;
  color: #fff !important;
  &:hover, &:focus {
    opacity: 0.92;
    transform: translateY(-1px);
  }
}
.fp-dialog .fp-dialog-btn--cancel.el-button {
  background: #fff !important;
  color: #64748b !important;
  border: 1px solid #e2e8f0 !important;
  &:hover, &:focus {
    background: #f8fafc !important;
    border-color: #cbd5e1 !important;
    color: #475569 !important;
  }
}

/* 新增/编辑表单内输入框圆角 */
.fp-dialog .derive-form {
  .el-input__inner,
  .el-textarea__inner {
    border-radius: 10px;
  }
  .el-form-item {
    margin-bottom: 16px;
  }
}
.fp-dialog .fp-dialog-textarea.el-textarea .el-textarea__inner {
  border-radius: 10px;
}
</style>

