<template>
  <view class="page">
    <!-- 头部欢迎区域 -->
    <view class="header">
      <text class="title">发票盒子</text>
      <text class="subtitle">智能识别 · 高效管理</text>
    </view>
    
    <!-- 主要功能卡片 -->
    <view class="content">
      <!-- 上传发票卡片 -->
      <view class="card upload-card">
        <view class="upload-area" @click="handleUpload">
          <view class="upload-icon">📷</view>
          <text class="upload-text">拍发票</text>
          <text class="upload-hint">支持增值税发票、普通发票等</text>
        </view>
        
        <view class="divider"></view>
        
        <view class="upload-area" @click="handleChooseFile">
          <view class="upload-icon">📁</view>
          <text class="upload-text">选文件</text>
          <text class="upload-hint">从相册选择图片或 PDF</text>
        </view>
      </view>
      
      <!-- 统计信息卡片 -->
      <view class="card stats-card">
        <view class="stats-item">
          <text class="stats-value">{{ stats.totalCount }}</text>
          <text class="stats-label">总发票数</text>
        </view>
        <view class="stats-divider"></view>
        <view class="stats-item">
          <text class="stats-value">{{ stats.recognizedCount }}</text>
          <text class="stats-label">已识别</text>
        </view>
        <view class="stats-divider"></view>
        <view class="stats-item">
          <text class="stats-value">¥{{ stats.totalAmount }}</text>
          <text class="stats-label">总金额</text>
        </view>
      </view>
      
      <!-- 快捷操作 -->
      <view class="quick-actions">
        <view class="action-btn" @click="goHistory">
          <text class="action-icon">📋</text>
          <text class="action-text">历史记录</text>
        </view>
        <view class="action-btn" @click="handleBatchUpload">
          <text class="action-icon">📑</text>
          <text class="action-text">批量上传</text>
        </view>
      </view>
    </view>
    
    <!-- 上传进度提示 -->
    <uni-load-more v-if="uploading" :contentText="{contentloading: '识别中...'}" />
  </view>
</template>

<script>
export default {
  data() {
    return {
      uploading: false,
      stats: {
        totalCount: 0,
        recognizedCount: 0,
        totalAmount: '0.00'
      }
    }
  },
  
  onLoad() {
    this.fetchStats()
  },
  
  methods: {
    // 获取统计数据
    async fetchStats() {
      try {
        // TODO: 调用 API 获取统计数据
        // const res = await this.$api.getStats()
        this.stats = {
          totalCount: 12,
          recognizedCount: 10,
          totalAmount: '12580.00'
        }
      } catch (error) {
        console.error('获取统计失败:', error)
      }
    },
    
    // 拍照上传
    handleUpload() {
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['camera'],
        success: (res) => {
          const tempFilePath = res.tempFilePaths[0]
          this.uploadInvoice(tempFilePath)
        },
        fail: (err) => {
          console.error('拍照失败:', err)
        }
      })
    },
    
    // 从相册选择
    handleChooseFile() {
      uni.chooseImage({
        count: 1,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: (res) => {
          const tempFilePath = res.tempFilePaths[0]
          this.uploadInvoice(tempFilePath)
        },
        fail: (err) => {
          console.error('选择文件失败:', err)
        }
      })
    },
    
    // 批量上传
    handleBatchUpload() {
      uni.chooseImage({
        count: 9,
        sizeType: ['compressed'],
        sourceType: ['album', 'camera'],
        success: (res) => {
          const tempFilePaths = res.tempFilePaths
          uni.showModal({
            title: '批量上传',
            content: `已选择 ${tempFilePaths.length} 张图片，确定要上传吗？`,
            success: (res) => {
              if (res.confirm) {
                this.uploadBatch(tempFilePaths)
              }
            }
          })
        }
      })
    },
    
    // 上传单张发票
    async uploadInvoice(filePath) {
      this.uploading = true
      
      try {
        // TODO: 调用上传 API
        // const res = await this.$api.uploadInvoice(filePath)
        
        uni.showLoading({ title: '识别中...' })
        
        // 模拟上传
        setTimeout(() => {
          uni.hideLoading()
          this.uploading = false
          uni.showToast({
            title: '上传成功',
            icon: 'success'
          })
          this.fetchStats()
          
          // 跳转到历史记录查看结果
          setTimeout(() => {
            this.goHistory()
          }, 1500)
        }, 2000)
        
      } catch (error) {
        this.uploading = false
        uni.showToast({
          title: '上传失败',
          icon: 'none'
        })
      }
    },
    
    // 批量上传
    async uploadBatch(filePaths) {
      uni.showLoading({
        title: '批量上传中...'
      })
      
      // TODO: 实现批量上传逻辑
      setTimeout(() => {
        uni.hideLoading()
        uni.showToast({
          title: '批量上传成功',
          icon: 'success'
        })
        this.fetchStats()
      }, 3000)
    },
    
    // 跳转到历史记录
    goHistory() {
      uni.switchTab({
        url: '/pages/history/history'
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
  padding-bottom: 120rpx;
}

.header {
  padding: 80rpx 40rpx 40rpx;
  text-align: center;
  
  .title {
    display: block;
    font-size: 48rpx;
    font-weight: bold;
    color: #fff;
    margin-bottom: 16rpx;
  }
  
  .subtitle {
    display: block;
    font-size: 28rpx;
    color: rgba(255, 255, 255, 0.8);
  }
}

.content {
  margin-top: -40rpx;
}

.card {
  background: #fff;
  border-radius: 24rpx;
  margin: 0 30rpx 30rpx;
  overflow: hidden;
}

.upload-card {
  .upload-area {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 60rpx 0;
    
    &:active {
      background: #f5f5f5;
    }
    
    .upload-icon {
      font-size: 80rpx;
      margin-bottom: 20rpx;
    }
    
    .upload-text {
      font-size: 32rpx;
      font-weight: bold;
      color: #333;
      margin-bottom: 12rpx;
    }
    
    .upload-hint {
      font-size: 24rpx;
      color: #999;
    }
  }
  
  .divider {
    height: 1rpx;
    background: #e5e5e5;
    margin: 0 40rpx;
  }
}

.stats-card {
  display: flex;
  align-items: center;
  justify-content: space-around;
  padding: 40rpx 0;
  
  .stats-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    
    .stats-value {
      font-size: 40rpx;
      font-weight: bold;
      color: #667eea;
      margin-bottom: 12rpx;
    }
    
    .stats-label {
      font-size: 24rpx;
      color: #999;
    }
  }
  
  .stats-divider {
    width: 1rpx;
    height: 80rpx;
    background: #e5e5e5;
  }
}

.quick-actions {
  display: flex;
  justify-content: space-around;
  padding: 20rpx 30rpx;
  
  .action-btn {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 30rpx 40rpx;
    background: #fff;
    border-radius: 20rpx;
    box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.08);
    
    &:active {
      transform: scale(0.95);
    }
    
    .action-icon {
      font-size: 48rpx;
      margin-bottom: 16rpx;
    }
    
    .action-text {
      font-size: 26rpx;
      color: #666;
    }
  }
}
</style>
