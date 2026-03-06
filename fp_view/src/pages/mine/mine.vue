<template>
  <view class="page">
    <!-- 用户信息卡片 -->
    <view class="user-card">
      <view class="user-info">
        <image class="avatar" :src="userInfo.avatar || '/static/default-avatar.png'" mode="aspectFill" />
        <view class="user-details">
          <text class="username">{{ userInfo.username || '未登录' }}</text>
          <text class="user-email">{{ userInfo.email || '点击登录' }}</text>
        </view>
      </view>
      <view v-if="!isLoggedIn" class="login-btn" @click="handleLogin">
        <text>立即登录</text>
      </view>
    </view>
    
    <!-- 功能菜单列表 -->
    <view class="menu-list">
      <!-- 数据统计 -->
      <view class="menu-item" @click="viewStats">
        <view class="menu-left">
          <text class="menu-icon">📊</text>
          <text class="menu-text">数据统计</text>
        </view>
        <view class="menu-right">
          <text class="menu-arrow">›</text>
        </view>
      </view>
      
      <!-- 发票导出 -->
      <view class="menu-item" @click="exportInvoices">
        <view class="menu-left">
          <text class="menu-icon">📥</text>
          <text class="menu-text">导出发票</text>
        </view>
        <view class="menu-right">
          <text class="menu-arrow">›</text>
        </view>
      </view>
      
      <!-- 批量识别 -->
      <view class="menu-item" @click="batchRecognize">
        <view class="menu-left">
          <text class="menu-icon">⚡</text>
          <text class="menu-text">批量识别</text>
        </view>
        <view class="menu-right">
          <text class="badge" v-if="pendingCount > 0">{{ pendingCount }}</text>
          <text class="menu-arrow">›</text>
        </view>
      </view>
      
      <!-- 设置 -->
      <view class="menu-item" @click="goSettings">
        <view class="menu-left">
          <text class="menu-icon">⚙️</text>
          <text class="menu-text">设置</text>
        </view>
        <view class="menu-right">
          <text class="menu-arrow">›</text>
        </view>
      </view>
      
      <!-- 关于我们 -->
      <view class="menu-item" @click="viewAbout">
        <view class="menu-left">
          <text class="menu-icon">ℹ️</text>
          <text class="menu-text">关于我们</text>
        </view>
        <view class="menu-right">
          <text class="menu-arrow">›</text>
        </view>
      </view>
    </view>
    
    <!-- 退出登录按钮 -->
    <view v-if="isLoggedIn" class="logout-btn" @click="handleLogout">
      <text>退出登录</text>
    </view>
    
    <!-- 版本信息 -->
    <view class="version-info">
      <text>Version {{ version }}</text>
    </view>
  </view>
</template>

<script>
export default {
  data() {
    return {
      version: '1.0.0',
      isLoggedIn: false,
      userInfo: {
        username: '',
        email: '',
        avatar: ''
      },
      pendingCount: 0
    }
  },
  
  onLoad() {
    this.checkLoginStatus()
    this.fetchPendingCount()
  },
  
  methods: {
    // 检查登录状态
    checkLoginStatus() {
      // TODO: 从本地存储或 API 检查登录状态
      const token = uni.getStorageSync('token')
      if (token) {
        this.isLoggedIn = true
        this.userInfo = {
          username: 'testuser',
          email: 'test@example.com',
          avatar: ''
        }
      }
    },
    
    // 获取待识别数量
    async fetchPendingCount() {
      try {
        // TODO: 调用 API 获取待识别数量
        this.pendingCount = 2
      } catch (error) {
        console.error('获取待识别数量失败:', error)
      }
    },
    
    // 登录
    handleLogin() {
      uni.navigateTo({
        url: '/pages/login/login'
      })
    },
    
    // 查看统计
    viewStats() {
      uni.showModal({
        title: '数据统计',
        content: `总发票数：12\n已识别：10\n待识别：2\n总金额：¥12580.00`,
        showCancel: false
      })
    },
    
    // 导出发票
    exportInvoices() {
      uni.showActionSheet({
        itemList: ['导出全部', '导出已识别', '导出最近一个月'],
        success: (res) => {
          uni.showLoading({ title: '生成中...' })
          
          // TODO: 调用导出 API
          setTimeout(() => {
            uni.hideLoading()
            uni.showToast({
              title: '导出成功',
              icon: 'success'
            })
          }, 1500)
        }
      })
    },
    
    // 批量识别
    batchRecognize() {
      if (this.pendingCount === 0) {
        uni.showToast({
          title: '没有待识别的发票',
          icon: 'none'
        })
        return
      }
      
      uni.showModal({
        title: '批量识别',
        content: `确定要批量识别 ${this.pendingCount} 张待识别发票吗？`,
        success: (res) => {
          if (res.confirm) {
            uni.showLoading({ title: '识别中...' })
            
            // TODO: 调用批量识别 API
            setTimeout(() => {
              uni.hideLoading()
              uni.showToast({
                title: '批量识别完成',
                icon: 'success'
              })
              this.pendingCount = 0
            }, 2000)
          }
        }
      })
    },
    
    // 设置
    goSettings() {
      uni.navigateTo({
        url: '/pages/settings/settings'
      })
    },
    
    // 关于我们
    viewAbout() {
      uni.showModal({
        title: '关于发票盒子',
        content: '发票盒子是一款智能发票识别管理工具，支持自动识别、批量处理、数据导出等功能，让发票管理更高效。',
        confirmText: '我知道了',
        showCancel: false
      })
    },
    
    // 退出登录
    handleLogout() {
      uni.showModal({
        title: '提示',
        content: '确定要退出登录吗？',
        success: (res) => {
          if (res.confirm) {
            // 清除本地 token
            uni.removeStorageSync('token')
            this.isLoggedIn = false
            this.userInfo = {
              username: '',
              email: '',
              avatar: ''
            }
            uni.showToast({
              title: '已退出登录',
              icon: 'success'
            })
          }
        }
      })
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

.user-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 60rpx 40rpx 40rpx;
  position: relative;
  
  .user-info {
    display: flex;
    align-items: center;
    
    .avatar {
      width: 120rpx;
      height: 120rpx;
      border-radius: 60rpx;
      border: 4rpx solid rgba(255, 255, 255, 0.3);
      background: #fff;
    }
    
    .user-details {
      margin-left: 30rpx;
      flex: 1;
      
      .username {
        display: block;
        font-size: 36rpx;
        font-weight: bold;
        color: #fff;
        margin-bottom: 12rpx;
      }
      
      .user-email {
        display: block;
        font-size: 26rpx;
        color: rgba(255, 255, 255, 0.8);
      }
    }
  }
  
  .login-btn {
    margin-top: 40rpx;
    background: rgba(255, 255, 255, 0.3);
    text-align: center;
    padding: 20rpx;
    border-radius: 50rpx;
    color: #fff;
    font-size: 28rpx;
    
    &:active {
      background: rgba(255, 255, 255, 0.2);
    }
  }
}

.menu-list {
  margin-top: 30rpx;
  background: #fff;
  
  .menu-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 36rpx 30rpx;
    border-bottom: 1rpx solid #f0f0f0;
    
    &:last-child {
      border-bottom: none;
    }
    
    &:active {
      background: #f5f5f5;
    }
    
    .menu-left {
      display: flex;
      align-items: center;
      
      .menu-icon {
        font-size: 40rpx;
        margin-right: 24rpx;
      }
      
      .menu-text {
        font-size: 30rpx;
        color: #333;
      }
    }
    
    .menu-right {
      display: flex;
      align-items: center;
      
      .badge {
        background: #ff4d4f;
        color: #fff;
        font-size: 20rpx;
        padding: 4rpx 16rpx;
        border-radius: 20rpx;
        margin-right: 16rpx;
      }
      
      .menu-arrow {
        font-size: 40rpx;
        color: #999;
      }
    }
  }
}

.logout-btn {
  margin: 60rpx 30rpx;
  background: #fff;
  text-align: center;
  padding: 28rpx;
  border-radius: 50rpx;
  font-size: 30rpx;
  color: #ff4d4f;
  box-shadow: 0 4rpx 12rpx rgba(0, 0, 0, 0.05);
  
  &:active {
    background: #fff1f0;
  }
}

.version-info {
  text-align: center;
  padding: 40rpx 0;
  
  text {
    font-size: 24rpx;
    color: #ccc;
  }
}
</style>
