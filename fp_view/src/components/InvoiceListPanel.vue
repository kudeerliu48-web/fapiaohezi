<template>
  <div class="panel list-panel">
    <div class="list-header">
      <span class="list-title">发票清单</span>
      <div class="list-tools">
        <el-input
          :value="searchKeyword"
          placeholder="搜索发票号 / 购买方 / 售卖方"
          prefix-icon="el-icon-search"
          clearable
          size="small"
          class="search-input"
          @clear="onSearchClear"
          @input="onSearchInput"
        />
        <el-button type="success" size="small" icon="el-icon-download" @click="exportExcel">导出Excel</el-button>
        <el-button type="danger" size="small" icon="el-icon-delete" :disabled="!selectedCount" @click="batchDelete">批量删除</el-button>
      </div>
    </div>

    <el-table
      :data="tableList"
      stripe
      class="invoice-table"
      :header-cell-style="{ background: '#f8fafc' }"
      v-loading="tableLoading"
      @selection-change="onSelectionChange"
      @row-click="onRowClick"
    >
      <el-table-column type="selection" width="48" />
      <el-table-column type="index" label="序号" width="60" align="center" />
      <el-table-column prop="invoice_number" label="发票号" min-width="140" show-overflow-tooltip />
      <el-table-column prop="buyer" label="购买方" min-width="160" show-overflow-tooltip />
      <el-table-column prop="seller" label="售卖方" min-width="160" show-overflow-tooltip />
      <el-table-column prop="invoice_amount" label="金额" width="110" align="right">
        <template slot-scope="scope">
          {{ formatMoney(scope.row.invoice_amount) }}
        </template>
      </el-table-column>
      <el-table-column prop="invoice_date" label="开票时间" width="120" align="center">
        <template slot-scope="scope">
          {{ formatDate(scope.row.invoice_date || scope.row.upload_time) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="170" align="center" fixed="right">
        <template slot-scope="scope">
          <el-button type="text" size="small" @click="previewRow(scope.row)">预览</el-button>
          <el-button type="text" size="small" @click="downloadRow(scope.row)">下载</el-button>
          <el-button type="text" size="small" class="danger-text" @click="deleteRow(scope.row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pager">
      <el-pagination
        @current-change="onPageChange"
        @size-change="onSizeChange"
        :current-page="page"
        :page-size="limit"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        :total="total"
      />
    </div>
  </div>
</template>

<script>
export default {
  name: 'InvoiceListPanel',
  props: {
    searchKeyword: {
      type: String,
      default: '',
    },
    tableList: {
      type: Array,
      default: () => [],
    },
    tableLoading: {
      type: Boolean,
      default: false,
    },
    selectedCount: {
      type: Number,
      default: 0,
    },
    page: {
      type: Number,
      default: 1,
    },
    limit: {
      type: Number,
      default: 10,
    },
    total: {
      type: Number,
      default: 0,
    },
    formatMoney: {
      type: Function,
      required: true,
    },
    formatDate: {
      type: Function,
      required: true,
    },
    onSearch: {
      type: Function,
      required: true,
    },
    exportExcel: {
      type: Function,
      required: true,
    },
    batchDelete: {
      type: Function,
      required: true,
    },
    previewRow: {
      type: Function,
      required: true,
    },
    downloadRow: {
      type: Function,
      required: true,
    },
    deleteRow: {
      type: Function,
      required: true,
    },
    onSelectionChangeParent: {
      type: Function,
      required: true,
    },
    onPageChange: {
      type: Function,
      required: true,
    },
    onSizeChange: {
      type: Function,
      required: true,
    },
  },
  methods: {
    onSearchInput(v) {
      this.$emit('update:searchKeyword', v)
      this.onSearch()
    },
    onSearchClear() {
      this.$emit('update:searchKeyword', '')
      this.onSearch()
    },
    onSelectionChange(rows) {
      this.onSelectionChangeParent(rows)
    },
    onRowClick(row) {
      this.previewRow(row)
    },
  },
}
</script>
