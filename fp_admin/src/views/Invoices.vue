<template>
  <div class="invoices-page">
    <el-card>
      <div slot="header" class="page-header">
        <span>发票列表</span>
      </div>
      
      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索发票号、购买方、销售方或文件名"
          style="width: 400px;"
          clearable
          @keyup.enter.native="handleSearch"
        >
          <el-button slot="append" icon="el-icon-search" @click="handleSearch">搜索</el-button>
        </el-input>
        <el-button type="success" icon="el-icon-download" @click="handleExport">导出 Excel</el-button>
      </div>
      
      <!-- 发票表格 -->
      <el-table
        :data="invoiceList"
        v-loading="loading"
        stripe
        border
        size="small"
        style="width: 100%"
      >
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="user_name" label="用户名" width="150" show-overflow-tooltip />
        <el-table-column
          prop="invoice_number"
          label="发票号码"
          width="200"
          class-name="col-invoice-number"
        />
        <el-table-column prop="invoice_amount" label="不含税额" width="120" align="right">
          <template slot-scope="scope">
            <span v-if="scope.row.invoice_amount">¥{{ scope.row.invoice_amount.toFixed(2) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_with_tax" label="价税合计" width="120" align="right">
          <template slot-scope="scope">
            <span v-if="scope.row.total_with_tax">¥{{ scope.row.total_with_tax.toFixed(2) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="buyer" label="购买方" width="200" show-overflow-tooltip />
        <el-table-column prop="seller" label="销售方" width="200" show-overflow-tooltip />
        <el-table-column prop="batch_id" label="批次号" width="300" show-overflow-tooltip />
        <el-table-column prop="recognition_status" label="识别状态" width="100">
          <template slot-scope="scope">
            <el-tag :type="getStatusType(scope.row.recognition_status)" size="small">
              {{ getStatusText(scope.row.recognition_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="上传时间" width="180">
          <template slot-scope="scope">
            {{ formatUploadTime(scope.row.upload_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="100">
          <template slot-scope="scope">
            <el-button
              type="primary"
              size="small"
              @click="handleViewDetail(scope.row)"
            >
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          :current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
    
    <!-- 详情对话框 -->
    <el-dialog
      title="发票详情"
      :visible.sync="detailDialogVisible"
      width="800px"
    >
      <div v-if="currentInvoice">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="用户名">{{ currentInvoice.user_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="发票号码">{{ currentInvoice.invoice_number || '-' }}</el-descriptions-item>
          <el-descriptions-item label="不含税额">
            <span v-if="currentInvoice.invoice_amount">¥{{ currentInvoice.invoice_amount.toFixed(2) }}</span>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="价税合计">
            <span v-if="currentInvoice.total_with_tax">¥{{ currentInvoice.total_with_tax.toFixed(2) }}</span>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="购买方">{{ currentInvoice.buyer || '-' }}</el-descriptions-item>
          <el-descriptions-item label="销售方">{{ currentInvoice.seller || '-' }}</el-descriptions-item>
          <el-descriptions-item label="识别状态">
            <el-tag :type="getStatusType(currentInvoice.recognition_status)" size="small">
              {{ getStatusText(currentInvoice.recognition_status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="批次号">{{ currentInvoice.batch_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="上传时间">{{ currentInvoice.upload_time }}</el-descriptions-item>
          <el-descriptions-item label="文件类型">{{ currentInvoice.file_type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">
            {{ formatFileSize(currentInvoice.file_size) }}
          </el-descriptions-item>
          <el-descriptions-item label="OCR 文本" :span="2">
            <el-input
              type="textarea"
              :rows="6"
              v-model="currentInvoice.ocr_text"
              readonly
            />
          </el-descriptions-item>
        </el-descriptions>

        <div class="attachment-preview">
          <img
            v-if="isImage(currentInvoice)"
            :src="currentInvoice.file_url"
            alt="发票预览"
            class="preview-image"
          />
          <iframe
            v-else-if="isPdf(currentInvoice) && currentInvoice.file_url"
            :src="pdfPreviewUrl(currentInvoice)"
            class="preview-iframe"
            title="PDF 预览"
          />
          <div v-else class="file-preview-fallback">
            <template v-if="currentInvoice.file_url">
              <p class="fallback-tip">该类型文件在页面内预览受限，可在新窗口中查看：</p>
              <el-button type="text" class="link-open-file" @click="openFile(currentInvoice)">在新窗口打开</el-button>
            </template>
            <p v-else class="fallback-tip">暂无文件路径</p>
          </div>
        </div>
      </div>
      <span slot="footer" class="dialog-footer">
        <el-button @click="detailDialogVisible = false">关 闭</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import { getAllInvoices, getInvoiceDetail, exportInvoices } from '@/api/invoice'

export default {
  name: 'Invoices',
  data() {
    return {
      invoiceList: [],
      loading: false,
      searchKeyword: '',
      currentPage: 1,
      pageSize: 10,
      total: 0,
      detailDialogVisible: false,
      currentInvoice: null
    }
  },
  
  created() {
    this.fetchInvoices()
  },
  
  methods: {
    async fetchInvoices() {
      this.loading = true
      try {
        const res = await getAllInvoices(this.currentPage, this.pageSize, this.searchKeyword)
        if (res.success) {
          this.invoiceList = res.data.invoices || []
          this.total = res.data.total || 0
        }
      } catch (error) {
        console.error('获取发票列表失败:', error)
      } finally {
        this.loading = false
      }
    },
    
    handleSearch() {
      this.currentPage = 1
      this.fetchInvoices()
    },
    
    handleSizeChange(val) {
      this.pageSize = val
      this.fetchInvoices()
    },
    
    handleCurrentChange(val) {
      this.currentPage = val
      this.fetchInvoices()
    },
    
    async handleViewDetail(row) {
      try {
        const res = await getInvoiceDetail(row.id)
        if (res.success) {
          this.currentInvoice = res.data
          this.detailDialogVisible = true
        }
      } catch (error) {
        console.error('获取发票详情失败:', error)
      }
    },
    
    async handleExport() {
      try {
        const res = await exportInvoices(this.searchKeyword)
        const blob = new Blob([res], { type: 'application/vnd.ms-excel' })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `发票导出_${new Date().getTime()}.xlsx`
        link.click()
        window.URL.revokeObjectURL(url)
        this.$message.success('导出成功')
      } catch (error) {
        console.error('导出失败:', error)
      }
    },

    formatUploadTime(val) {
      if (!val) return '-'
      const s = String(val).replace('T', ' ')
      return s.length >= 19 ? s.slice(0, 19) : s
    },
    
    getStatusType(status) {
      const types = {
        0: 'info',
        1: 'success',
        2: 'danger'
      }
      return types[status] || 'info'
    },
    
    getStatusText(status) {
      const texts = {
        0: '待识别',
        1: '已识别',
        2: '识别失败'
      }
      return texts[status] || '未知'
    },
    
    formatFileSize(bytes) {
      if (!bytes) return '-'
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
    },

    isImage(inv) {
      if (!inv) return false
      const src = inv.file_url || inv.filename || ''
      if (!src) return false
      const ext = src.split('.').pop().toLowerCase()
      return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext)
    },

    isPdf(inv) {
      if (!inv) return false
      const src = inv.file_url || inv.filename || ''
      if (!src) return false
      const ext = src.split('.').pop().toLowerCase()
      return ext === 'pdf'
    },

    pdfPreviewUrl(inv) {
      const url = inv && inv.file_url
      if (!url) return ''
      return url + (url.indexOf('#') >= 0 ? '&' : '#') + 'toolbar=0'
    },

    openFile(inv) {
      const url = inv && inv.file_url
      if (url) window.open(url, '_blank')
    },
  }
}
</script>

<style scoped lang="scss">
.invoices-page {
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 16px;
    font-weight: bold;
  }
  
  .search-bar {
    display: flex;
    justify-content: space-between;
    margin-bottom: 20px;
  }
  
  .pagination-container {
    margin-top: 20px;
    text-align: right;
  }

  /* 表格紧凑 + 文本省略号 */
  ::v-deep .el-table {
    font-size: 13px;
    
    // 网格边框增强
    th.el-table__cell,
    td.el-table__cell {
      border: 1px solid #EBEEF5;
    }
    
    th.el-table__cell {
      background-color: #F5F7FA;
      color: #606266;
      font-weight: 600;
    }
    
    .el-table__body tr:hover > td {
      background-color: #ecf5ff;
    }
  }
  
  ::v-deep .el-table th,
  ::v-deep .el-table td {
    padding: 6px 8px;
  }
  ::v-deep .el-table .cell {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* 发票号码列：允许显示完整内容 */
  ::v-deep .col-invoice-number .cell {
    text-overflow: initial;
  }

  .invoice-image-wrapper {
    margin-top: 16px;
    text-align: center;

    img {
      max-width: 100%;
      max-height: 360px;
      border-radius: 8px;
      box-shadow: 0 8px 24px rgba(15, 23, 42, 0.25);
    }
  }
}
</style>
