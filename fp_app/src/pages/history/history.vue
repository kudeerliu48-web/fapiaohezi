<template>
  <view class="page">
    <!-- 搜索栏 -->
    <view class="search-bar">
      <view class="search-input" @click="handleSearch">
        <text class="search-icon">🔍</text>
        <text class="search-placeholder">搜索发票号、购买方...</text>
      </view>
    </view>
    
    <!-- 发票列表 -->
    <scroll-view scroll-y class="invoice-list">
      <view v-for="(item, index) in invoiceList" :key="index" class="invoice-card" @click="viewDetail(item)">
        <view class="invoice-header">
          <text class="invoice-title">{{ item.filename || '发票' }}</text>
          <text :class="['status-tag', getStatusClass(item.recognition_status)]">
            {{ getStatusText(item.recognition_status) }}
          </text>
        </view>
        
        <view class="invoice-body">
          <view class="invoice-row">
            <text class="invoice-label">发票号码：</text>
            <text class="invoice-value">{{ item.invoice_number || '-' }}</text>
          </view>
          <view class="invoice-row">
            <text class="invoice-label">发票金额：</text>
            <text class="invoice-value amount">¥{{ item.invoice_amount || 0 }}</text>
          </view>
          <view class="invoice-row">
            <text class="invoice-label">购买方：</text>
            <text class="invoice-value">{{ item.buyer || '-' }}</text>
          </view>
          <view class="invoice-row">
            <text class="invoice-label">识别时间：</text>
            <text class="invoice-value time">{{ formatTime(item.upload_time) }}</text>
          </view>
        </view>
        
        <view class="invoice-footer">
          <text class="action-link" @click.stop="recognizeInvoice(item)">重新识别</text>
          <text class="action-link" @click.stop="deleteInvoice(item)">删除</text>
        </view>
      </view>
      
      <!-- 空状态 -->
      <view v-if="invoiceList.length === 0" class="empty-state">
        <text class="empty-icon">📄</text>
        <text class="empty-text">暂无发票记录</text>
        <text class="empty-hint">快去上传第一张发票吧~</text>
      </view>
    </scroll-view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      invoiceList: [],
      keyword: ''
    }
  },
  
  onLoad() {
    this.loadInvoices()
  },
  
  onPullDownRefresh() {
    this.refresh()
  },
  
  methods: {
    async loadInvoices(refresh = false) {
      // TODO: 调用 API 获取发票列表
      const mockData = [
        {
          id: '1',
          filename: '增值税电子发票.pdf',
          invoice_number: '033060829',
          invoice_amount: 1256.00,
          buyer: '某某科技有限公司',
          recognition_status: 1,
          upload_time: new Date().getTime()
        }
      ]
      
      if (refresh) {
        this.invoiceList = mockData
      } else {
        this.invoiceList.push(...mockData)
      }
      
      uni.stopPullDownRefresh()
    },
    
    refresh() {
      this.loadInvoices(true)
    },
    
    handleSearch() {
      uni.showModal({
        title: '搜索发票',
        editable: true,
        placeholderText: '请输入发票号或购买方名称',
        success: (res) => {
          if (res.confirm && res.content) {
            this.keyword = res.content
            this.refresh()
          }
        }
      })
    },
    
    viewDetail(item) {
      uni.navigateTo({
        url: `/pages/invoice-detail/invoice-detail?id=${item.id}`
      })
    },
    
    recognizeInvoice(item) {
      uni.showModal({
        title: '提示',
        content: '确定要重新识别这张发票吗？',
        success: (res) => {
          if (res.confirm) {
            uni.showToast({
              title: '开始重新识别',
              icon: 'none'
            })
          }
        }
      })
    },
    
    deleteInvoice(item) {
      uni.showModal({
        title: '提示',
        content: '确定要删除这张发票吗？',
        confirmColor: '#ff4d4f',
        success: (res) => {
          if (res.confirm) {
            const index = this.invoiceList.findIndex(i => i.id === item.id)
            if (index !== -1) {
              this.invoiceList.splice(index, 1)
            }
            uni.showToast({
              title: '删除成功',
              icon: 'success'
            })
          }
        }
      })
    },
    
    getStatusClass(status) {
      const classes = { 0: 'status-pending', 1: 'status-success', 2: 'status-failed' }
      return classes[status] || 'status-pending'
    },
    
    getStatusText(status) {
      const texts = { 0: '待识别', 1: '已识别', 2: '识别失败' }
      return texts[status] || '未知'
    },
    
    formatTime(timestamp) {
      if (!timestamp) return '-'
      const date = new Date(timestamp)
      return `${date.getMonth() + 1}月${date.getDate()}日`
    }
  }
}
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  background: #f5f5f5;
}

.search-bar {
  background: #fff;
  padding: 20rpx 30rpx;
  box-shadow: 0 2rpx 8rpx rgba(0, 0, 0, 0.05);
  
  .search-input {
    display: flex;
    align-items: center;
    background: #f5f5f5;
    border-radius: 50rpx;
    padding: 20rpx 30rpx;
    
    .search-icon {
      font-size: 32rpx;
      margin-right: 16rpx;
    }
    
    .search-placeholder {
      font-size: 28rpx;
      color: #999;
    }
  }
}

.invoice-list {
  height: calc(100vh - 140rpx);
  padding: 20rpx;
}

.invoice-card {
  background: #fff;
  border-radius: 16rpx;
  padding: 30rpx;
  margin-bottom: 20rpx;
  box-shadow: 0 2rpx 12rpx rgba(0, 0, 0, 0.05);
  
  .invoice-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24rpx;
    
    .invoice-title {
      font-size: 30rpx;
      font-weight: bold;
      color: #333;
    }
    
    .status-tag {
      padding: 8rpx 20rpx;
      border-radius: 20rpx;
      font-size: 22rpx;
      
      &.status-pending {
        background: #f0f0f0;
        color: #999;
      }
      
      &.status-success {
        background: #e6f7ed;
        color: #52c41a;
      }
      
      &.status-failed {
        background: #fff1f0;
        color: #ff4d4f;
      }
    }
  }
  
  .invoice-body {
    .invoice-row {
      display: flex;
      margin-bottom: 16rpx;
      
      .invoice-label {
        font-size: 26rpx;
        color: #999;
        min-width: 140rpx;
      }
      
      .invoice-value {
        font-size: 26rpx;
        color: #333;
        flex: 1;
        
        &.amount {
          color: #ff6b00;
          font-weight: bold;
        }
        
        &.time {
          color: #999;
        }
      }
    }
  }
  
  .invoice-footer {
    display: flex;
    justify-content: flex-end;
    margin-top: 24rpx;
    padding-top: 24rpx;
    border-top: 1rpx solid #f0f0f0;
    
    .action-link {
      font-size: 26rpx;
      color: #667eea;
      margin-left: 30rpx;
    }
  }
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 120rpx 0;
  
  .empty-icon {
    font-size: 120rpx;
    margin-bottom: 30rpx;
  }
  
  .empty-text {
    font-size: 32rpx;
    color: #999;
    margin-bottom: 16rpx;
  }
  
  .empty-hint {
    font-size: 26rpx;
    color: #ccc;
  }
}
</style>
