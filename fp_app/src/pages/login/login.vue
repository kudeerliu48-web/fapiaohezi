<template>
  <view class="page">
    <view class="login-container">
      <text class="title">欢迎登录</text>
      <text class="subtitle">发票盒子管理系统</text>
      
      <view class="form">
        <view class="input-item">
          <input v-model="username" type="text" placeholder="请输入用户名" class="input" />
        </view>
        
        <view class="input-item">
          <input v-model="password" type="password" placeholder="请输入密码" class="input" />
        </view>
        
        <view class="login-btn" @click="handleLogin">
          <text>登 录</text>
        </view>
        
        <view class="tips">
          <text class="tip-text">测试账号：testuser / test123456</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script>
import api from '@/utils/api.js'

export default {
  data() {
    return {
      username: '',
      password: ''
    }
  },
  
  methods: {
    async handleLogin() {
      if (!this.username || !this.password) {
        uni.showToast({
          title: '请输入用户名和密码',
          icon: 'none'
        })
        return
      }
      
      try {
        uni.showLoading({ title: '登录中...' })
        
        const res = await api.login({
          username: this.username,
          password: this.password
        })
        
        uni.setStorageSync('token', res.data.token || 'test-token')
        
        uni.hideLoading()
        uni.showToast({
          title: '登录成功',
          icon: 'success'
        })
        
        setTimeout(() => {
          uni.navigateBack()
        }, 1500)
        
      } catch (error) {
        uni.hideLoading()
        console.error('登录失败:', error)
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40rpx;
}

.login-container {
  width: 100%;
  background: #fff;
  border-radius: 24rpx;
  padding: 80rpx 60rpx;
  box-shadow: 0 10rpx 40rpx rgba(0, 0, 0, 0.1);
  
  .title {
    display: block;
    font-size: 48rpx;
    font-weight: bold;
    color: #333;
    text-align: center;
    margin-bottom: 20rpx;
  }
  
  .subtitle {
    display: block;
    font-size: 28rpx;
    color: #999;
    text-align: center;
    margin-bottom: 80rpx;
  }
  
  .form {
    .input-item {
      margin-bottom: 40rpx;
      
      .input {
        width: 100%;
        height: 88rpx;
        background: #f5f5f5;
        border-radius: 44rpx;
        padding: 0 40rpx;
        font-size: 30rpx;
      }
    }
    
    .login-btn {
      width: 100%;
      height: 88rpx;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      border-radius: 44rpx;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 32rpx;
      font-weight: bold;
      margin-top: 60rpx;
      
      &:active {
        opacity: 0.9;
        transform: scale(0.98);
      }
    }
    
    .tips {
      margin-top: 40rpx;
      text-align: center;
      
      .tip-text {
        font-size: 24rpx;
        color: #999;
      }
    }
  }
}
</style>
