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
    <scroll-view scroll-y class="invoice-list" @scrolltolower="loadMore">
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
      <view v-if="invoiceList.length === 0 && !loading" class="empty-state">
        <text class="empty-icon">📄</text>
        <text class="empty-text">暂无发票记录</text>
        <text class="empty-hint">快去上传第一张发票吧~</text>
      </view>
      
      <!-- 加载更多 -->
      <view v-if="loading" class="loading-more">
        <uni-load-more :contentText="{contentloading: '加载中...'}" />
      </view>
      
      <!-- 没有更多数据 -->
      <view v-if="noMoreData && invoiceList.length > 0" class="no-more">
        <text class="no-more-text">- 已经到底了 -</text>
      </view>
    </scroll-view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      loading: false,
      invoiceList: [],
      page: 1,
      limit: 10,
      noMoreData: false,
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
    // 加载发票列表
    async loadInvoices(refresh = false) {
      if (this.loading) return
      
      this.loading = true
      
      try {
        // TODO: 调用 API 获取发票列表
        // const res = await this.$api.getInvoices(this.page, this.limit, this.keyword)
        
        // 模拟数据
        const mockData = [
          {
            id: '1',
            filename: '增值税电子发票.pdf',
            invoice_number: '033060829',
            invoice_amount: 1256.00,
            buyer: '某某科技有限公司',
            recognition_status: 1,
            upload_time: new Date().getTime()
          },
          {
            id: '2',
            filename: '北京增值税发票.jpg',
            invoice_number: '044012345',
            invoice_amount: 5680.50,
            buyer: '某某贸易公司',
            recognition_status: 1,
            upload_time: new Date().getTime() - 86400000
          }
        ]
        
        if (refresh) {
          this.invoiceList = mockData
        } else {
          this.invoiceList.push(mockData)
        }
        
        this.page++
        this.noMoreData = mockData.length < this.limit
        
      } catch (error) {
        console.error('加载发票失败:', error)
        uni.showToast({
          title: '加载失败',
          icon: 'none'
        })
      } finally {
        this.loading = false
        uni.stopPullDownRefresh()
      }
    },
    
    // 刷新
    refresh() {
      this.page = 1
      this.noMoreData = false
      this.loadInvoices(true)
    },
    
    // 加载更多
    loadMore() {
      if (!this.noMoreData) {
        this.loadInvoices()
      }
    },
    
    // 搜索
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
    
    // 查看详情
    viewDetail(item) {
      uni.navigateTo({
        url: `/pages/invoice-detail/invoice-detail?id=${item.id}`
      })
    },
    
    // 重新识别
    recognizeInvoice(item) {
      uni.showModal({
        title: '提示',
        content: '确定要重新识别这张发票吗？',
        success: (res) => {
          if (res.confirm) {
            // TODO: 调用重新识别 API
            uni.showToast({
              title: '开始重新识别',
              icon: 'none'
            })
          }
        }
      })
    },
    
    // 删除发票
    deleteInvoice(item) {
      uni.showModal({
        title: '提示',
        content: '确定要删除这张发票吗？此操作不可恢复',
        confirmColor: '#ff4d4f',
        success: (res) => {
          if (res.confirm) {
            // TODO: 调用删除 API
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
    
    // 获取状态样式类名
    getStatusClass(status) {
      const classes = {
        0: 'status-pending',
        1: 'status-success',
        2: 'status-failed'
      }
      return classes[status] || 'status-pending'
    },
    
    // 获取状态文本
    getStatusText(status) {
      const texts = {
        0: '待识别',
        1: '已识别',
        2: '识别失败'
      }
      return texts[status] || '未知'
    },
    
    // 格式化时间
    formatTime(timestamp) {
      if (!timestamp) return '-'
      const date = new Date(timestamp)
      const now = new Date()
      const diff = now - date
      
      if (diff < 60000) return '刚刚'
      if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
      if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
      if (diff < 604800000) return `${Math.floor(diff / 86400000)}天前`
      
      return `${date.getMonth() + 1}月${date.getDate()}日`
    }
  }
}
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  background: #f5f5f5;
  padding-bottom: env(safe-area-inset-bottom);
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
  
  &:active {
    transform: scale(0.98);
  }
  
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
      
      &:last-child {
        margin-bottom: 0;
      }
      
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
      
      &:active {
        opacity: 0.6;
      }
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

.loading-more,
.no-more {
  text-align: center;
  padding: 30rpx 0;
  
  .no-more-text {
    font-size: 24rpx;
    color: #999;
  }
}
</style>
