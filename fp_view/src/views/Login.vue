<template>
  <div class="login-container">
    <div class="login-card">
      <div class="card-header">
        <div class="logo-section">
          <div class="logo-icon">📋</div>
          <h1 class="app-title">发票盒子</h1>
          <p class="app-subtitle">智能发票管理系统</p>
        </div>
      </div>
      
      <div class="card-body">
        <el-tabs v-model="activeTab" class="auth-tabs">
          <!-- 登录标签页 -->
          <el-tab-pane label="登录" name="login">
            <el-form 
              ref="loginForm" 
              :model="loginForm" 
              :rules="loginRules" 
              class="auth-form"
              @submit.native.prevent="handleLogin"
            >
              <el-form-item prop="username">
                <el-input
                  v-model="loginForm.username"
                  placeholder="请输入用户名"
                  prefix-icon="el-icon-user"
                  size="large"
                  clearable
                />
              </el-form-item>
              
              <el-form-item prop="password">
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  placeholder="请输入密码"
                  prefix-icon="el-icon-lock"
                  size="large"
                  show-password
                  clearable
                  @keyup.enter.native="handleLogin"
                />
              </el-form-item>
              
              <el-form-item>
                <el-button 
                  type="primary" 
                  size="large" 
                  class="auth-button"
                  :loading="loginLoading"
                  @click="handleLogin"
                >
                  {{ loginLoading ? '登录中...' : '登录' }}
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
          
          <!-- 注册标签页 -->
          <el-tab-pane label="注册" name="register">
            <el-form 
              ref="registerForm" 
              :model="registerForm" 
              :rules="registerRules" 
              class="auth-form"
              @submit.native.prevent="handleRegister"
            >
              <el-form-item prop="username">
                <el-input
                  v-model="registerForm.username"
                  placeholder="请输入用户名"
                  prefix-icon="el-icon-user"
                  size="large"
                  clearable
                />
              </el-form-item>
              
              <el-form-item prop="password">
                <el-input
                  v-model="registerForm.password"
                  type="password"
                  placeholder="请输入密码"
                  prefix-icon="el-icon-lock"
                  size="large"
                  show-password
                  clearable
                />
              </el-form-item>
              
              <el-form-item prop="confirmPassword">
                <el-input
                  v-model="registerForm.confirmPassword"
                  type="password"
                  placeholder="请确认密码"
                  prefix-icon="el-icon-lock"
                  size="large"
                  show-password
                  clearable
                />
              </el-form-item>
              
              <el-form-item prop="email">
                <el-input
                  v-model="registerForm.email"
                  placeholder="请输入邮箱"
                  prefix-icon="el-icon-message"
                  size="large"
                  clearable
                />
              </el-form-item>
              
              <el-form-item prop="company">
                <el-input
                  v-model="registerForm.company"
                  placeholder="请输入公司名称（可选）"
                  prefix-icon="el-icon-office-building"
                  size="large"
                  clearable
                />
              </el-form-item>
              
              <el-form-item prop="phone">
                <el-input
                  v-model="registerForm.phone"
                  placeholder="请输入手机号码（可选）"
                  prefix-icon="el-icon-phone"
                  size="large"
                  clearable
                />
              </el-form-item>
              
              <el-form-item>
                <el-button 
                  type="primary" 
                  size="large" 
                  class="auth-button"
                  :loading="registerLoading"
                  @click="handleRegister"
                >
                  {{ registerLoading ? '注册中...' : '注册' }}
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Login',
  data() {
    // 密码验证规则
    const validatePassword = (rule, value, callback) => {
      if (value === '') {
        callback(new Error('请输入密码'))
      } else if (value.length < 6) {
        callback(new Error('密码长度不能少于6位'))
      } else {
        callback()
      }
    }
    
    // 确认密码验证规则
    const validateConfirmPassword = (rule, value, callback) => {
      if (value === '') {
        callback(new Error('请确认密码'))
      } else if (value !== this.registerForm.password) {
        callback(new Error('两次输入密码不一致'))
      } else {
        callback()
      }
    }
    
    return {
      activeTab: 'login',
      loginLoading: false,
      registerLoading: false,
      
      // 登录表单
      loginForm: {
        username: '',
        password: ''
      },
      
      // 注册表单
      registerForm: {
        username: '',
        password: '',
        confirmPassword: '',
        email: '',
        company: '',
        phone: ''
      },
      
      // 登录表单验证规则
      loginRules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' },
          { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { validator: validatePassword, trigger: 'blur' }
        ]
      },
      
      // 注册表单验证规则
      registerRules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' },
          { min: 3, max: 20, message: '用户名长度在 3 到 20 个字符', trigger: 'blur' }
        ],
        password: [
          { required: true, message: '请输入密码', trigger: 'blur' },
          { validator: validatePassword, trigger: 'blur' }
        ],
        confirmPassword: [
          { required: true, message: '请确认密码', trigger: 'blur' },
          { validator: validateConfirmPassword, trigger: 'blur' }
        ],
        email: [
          { required: true, message: '请输入邮箱', trigger: 'blur' },
          { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
        ],
        company: [
          { max: 50, message: '公司名称不能超过50个字符', trigger: 'blur' }
        ],
        phone: [
          { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的手机号码', trigger: 'blur' }
        ]
      }
    }
  },
  
  methods: {
    // 处理登录
    async handleLogin() {
      try {
        await this.$refs.loginForm.validate()
        this.loginLoading = true
        
        const response = await axios.post('http://localhost:8000/api/login', {
          username: this.loginForm.username,
          password: this.loginForm.password
        })
        
        if (response.data.success) {
          // 保存用户信息到localStorage
          localStorage.setItem('user', JSON.stringify(response.data.data.user))
          localStorage.setItem('token', 'mock-token') // 实际项目中使用真实token
          
          this.$message.success('登录成功')
          
          // 跳转到首页
          this.$router.push('/')
        } else {
          this.$message.error(response.data.message || '登录失败')
        }
      } catch (error) {
        console.error('登录错误:', error)
        if (error.response && error.response.data) {
          this.$message.error(error.response.data.message || '登录失败')
        } else {
          this.$message.error('网络错误，请稍后重试')
        }
      } finally {
        this.loginLoading = false
      }
    },
    
    // 处理注册
    async handleRegister() {
      try {
        await this.$refs.registerForm.validate()
        this.registerLoading = true
        
        const response = await axios.post('http://localhost:8000/api/register', {
          username: this.registerForm.username,
          password: this.registerForm.password,
          email: this.registerForm.email,
          company: this.registerForm.company,
          phone: this.registerForm.phone
        })
        
        if (response.data.success) {
          this.$message.success('注册成功，请登录')
          
          // 切换到登录标签页
          this.activeTab = 'login'
          
          // 清空注册表单
          this.registerForm = {
            username: '',
            password: '',
            confirmPassword: '',
            email: '',
            company: '',
            phone: ''
          }
          
          // 预填用户名
          this.loginForm.username = response.data.data.user_id
        } else {
          this.$message.error(response.data.message || '注册失败')
        }
      } catch (error) {
        console.error('注册错误:', error)
        if (error.response && error.response.data) {
          this.$message.error(error.response.data.message || '注册失败')
        } else {
          this.$message.error('网络错误，请稍后重试')
        }
      } finally {
        this.registerLoading = false
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 35%, #f1f5f9 70%, #e0e7ff 100%);
  position: relative;
  overflow: hidden;
  
  // 背景装饰
  &::before {
    content: '';
    position: absolute;
    top: -100px;
    right: -100px;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(99, 102, 241, 0.1), transparent);
    border-radius: 50%;
    animation: float 15s ease-in-out infinite;
  }
  
  &::after {
    content: '';
    position: absolute;
    bottom: -80px;
    left: -80px;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(139, 92, 246, 0.1), transparent);
    border-radius: 50%;
    animation: float 12s ease-in-out infinite reverse;
  }
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -20px) scale(1.05); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}

.login-card {
  width: 100%;
  max-width: 480px;
  margin: 20px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1), 0 8px 24px rgba(0, 0, 0, 0.06);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  overflow: hidden;
  position: relative;
  z-index: 1;
}

.card-header {
  padding: 40px 40px 20px;
  background: linear-gradient(135deg, #f0f4f8 0%, #e8edf2 100%);
  border-bottom: 1px solid rgba(99, 102, 241, 0.08);
  text-align: center;
}

.logo-section {
  .logo-icon {
    font-size: 48px;
    margin-bottom: 16px;
    filter: drop-shadow(0 0 20px rgba(99, 102, 241, 0.3));
    animation: glow 3s ease-in-out infinite;
  }
  
  .app-title {
    font-size: 28px;
    font-weight: 700;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 8px;
    letter-spacing: -0.5px;
  }
  
  .app-subtitle {
    font-size: 14px;
    color: #64748b;
    margin: 0;
    font-weight: 400;
  }
}

@keyframes glow {
  0%, 100% { filter: drop-shadow(0 0 20px rgba(99, 102, 241, 0.3)); }
  50% { filter: drop-shadow(0 0 30px rgba(99, 102, 241, 0.5)); }
}

.card-body {
  padding: 40px;
}

.auth-tabs {
  ::v-deep .el-tabs__header {
    margin: 0 0 32px;
  }
  
  ::v-deep .el-tabs__nav-wrap {
    &::after {
      display: none;
    }
  }
  
  ::v-deep .el-tabs__item {
    font-size: 16px;
    font-weight: 600;
    color: #64748b;
    padding: 0 0 12px;
    margin-right: 32px;
    
    &.is-active {
      color: #6366f1;
    }
    
    &:hover {
      color: #a78bfa;
    }
  }
  
  ::v-deep .el-tabs__active-bar {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    height: 3px;
    border-radius: 2px;
  }
}

.auth-form {
  .el-form-item {
    margin-bottom: 24px;
    
    &:last-child {
      margin-bottom: 0;
    }
  }
  
  ::v-deep .el-input__inner {
    height: 48px;
    line-height: 48px;
    border-radius: 12px;
    border: 2px solid #e2e8f0;
    background: rgba(255, 255, 255, 0.9);
    transition: all 0.2s ease;
    
    &:focus {
      border-color: #6366f1;
      background: rgba(255, 255, 255, 0.95);
      box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.08);
    }
    
    &:hover {
      border-color: #cbd5e1;
    }
  }
  
  ::v-deep .el-input__prefix {
    left: 16px;
    color: #94a3b8;
  }
  
  ::v-deep .el-input__suffix {
    right: 16px;
  }
  
  ::v-deep .el-input__inner {
    padding-left: 44px;
    padding-right: 44px;
  }
}

.auth-button {
  width: 100%;
  height: 48px;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  border: none;
  box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
  transition: all 0.2s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
  }
  
  &:active {
    transform: translateY(0);
  }
  
  &.is-loading {
    opacity: 0.8;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .login-card {
    margin: 16px;
    border-radius: 20px;
  }
  
  .card-header {
    padding: 32px 24px 16px;
  }
  
  .card-body {
    padding: 32px 24px;
  }
  
  .logo-section {
    .logo-icon {
      font-size: 40px;
    }
    
    .app-title {
      font-size: 24px;
    }
  }
  
  .auth-tabs {
    ::v-deep .el-tabs__item {
      font-size: 14px;
      margin-right: 24px;
    }
  }
}

@media (max-width: 480px) {
  .login-card {
    margin: 12px;
    border-radius: 16px;
  }
  
  .card-header {
    padding: 24px 20px 12px;
  }
  
  .card-body {
    padding: 24px 20px;
  }
}
</style>
