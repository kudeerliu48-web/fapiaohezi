<template>
  <div class="auth-page">
    <div class="bg-decoration">
      <div class="glow-sphere sphere-1" />
      <div class="glow-sphere sphere-2" />
      <div class="glow-sphere sphere-3" />
    </div>

    <div class="auth-shell">
      <section class="brand-panel">
        <div class="brand-content">
          <div class="brand-badge">发票盒子 · 企业版</div>
          <h1>发票盒子</h1>
          <div class="brand-desc">
            <p>手机号一键接入，开启智能化财税管理新时代。</p>
            <ul class="feature-list">
              <li><i class="el-icon-circle-check"></i> 毫秒级发票OCR识别</li>
              <li><i class="el-icon-circle-check"></i> 自动化邮箱导入技术</li>
              <li><i class="el-icon-circle-check"></i> 全流程合规风控追踪</li>
            </ul>
          </div>
        </div>
      </section>

      <section class="form-panel">
        <div class="panel-head">
          <h2>{{ activeTab === 'login' ? '欢迎回来' : '注册新账号' }}</h2>
          <p class="subtitle">{{ activeTab === 'login' ? '请选择您偏好的方式登录系统' : '只需几步，开启高效报销体验' }}</p>
        </div>

        <el-tabs v-model="activeTab" class="auth-tabs" stretch>
          <el-tab-pane label="登 录" name="login">
            <div class="mode-switch-wrapper">
              <el-radio-group v-model="loginMode" size="medium" class="custom-radio">
                <el-radio-button label="password">密码登录</el-radio-button>
                <el-radio-button label="sms">验证码登录</el-radio-button>
              </el-radio-group>
            </div>

            <transition name="form-fade" mode="out-in">
              <el-form
                v-if="loginMode === 'password'"
                key="pwd"
                ref="passwordLoginFormRef"
                :model="passwordLoginForm"
                :rules="passwordLoginRules"
                class="animated-form"
                @submit.native.prevent
              >
                <el-form-item prop="phone">
                  <el-input v-model.trim="passwordLoginForm.phone" placeholder="手机号码" prefix-icon="el-icon-user" />
                </el-form-item>
                <el-form-item prop="password">
                  <el-input
                    v-model="passwordLoginForm.password"
                    type="password"
                    placeholder="登录密码"
                    prefix-icon="el-icon-lock"
                    show-password
                    @keyup.enter.native="handlePasswordLogin"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" class="gradient-btn" :loading="passwordLoginLoading" @click="handlePasswordLogin">
                    {{ passwordLoginLoading ? '正在验证...' : '立即登录' }}
                  </el-button>
                </el-form-item>
              </el-form>

              <el-form
                v-else
                key="sms"
                ref="smsLoginFormRef"
                :model="smsLoginForm"
                :rules="smsLoginRules"
                class="animated-form"
                @submit.native.prevent
              >
                <el-form-item prop="phone">
                  <el-input v-model.trim="smsLoginForm.phone" placeholder="手机号码" prefix-icon="el-icon-user" />
                </el-form-item>
                <el-form-item prop="sms_code">
                  <el-input v-model.trim="smsLoginForm.sms_code" placeholder="6位验证码" prefix-icon="el-icon-chat-line-round">
                    <el-button slot="append" :disabled="loginSmsCountdown > 0" class="code-btn" @click="sendLoginSmsCode">
                      {{ loginSmsCountdown > 0 ? `${loginSmsCountdown}s` : '获取验证码' }}
                    </el-button>
                  </el-input>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" class="gradient-btn" :loading="smsLoginLoading" @click="handleSMSLogin">
                    {{ smsLoginLoading ? '正在验证...' : '验证码登录' }}
                  </el-button>
                </el-form-item>
              </el-form>
            </transition>
          </el-tab-pane>

          <el-tab-pane label="注 册" name="register">
            <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" class="animated-form" @submit.native.prevent>
              <el-form-item prop="phone">
                <el-input v-model.trim="registerForm.phone" placeholder="手机号码" prefix-icon="el-icon-user" />
              </el-form-item>
              <el-form-item prop="password">
                <el-input v-model="registerForm.password" type="password" placeholder="设置密码 (至少6位)" prefix-icon="el-icon-lock" show-password />
              </el-form-item>
              <el-form-item prop="confirmPassword">
                <el-input v-model="registerForm.confirmPassword" type="password" placeholder="确认密码" prefix-icon="el-icon-circle-check" show-password />
              </el-form-item>
              <el-form-item prop="sms_code">
                <el-input v-model.trim="registerForm.sms_code" placeholder="验证码" prefix-icon="el-icon-chat-line-round">
                  <el-button slot="append" :disabled="registerSmsCountdown > 0" class="code-btn" @click="sendRegisterSmsCode">
                    {{ registerSmsCountdown > 0 ? `${registerSmsCountdown}s` : '获取验证码' }}
                  </el-button>
                </el-input>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" class="gradient-btn register-btn" :loading="registerLoading" @click="handleRegister">
                  {{ registerLoading ? '账号创建中...' : '注册新账号' }}
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </section>
    </div>
  </div>
</template>

<script>
import { authAPI } from '@/api/auth'

const PHONE_REG = /^1\d{10}$/

export default {
  name: 'Login',
  data() {
    const validatePhone = (rule, value, callback) => {
      if (!value) return callback(new Error('请输入手机号码'))
      if (!PHONE_REG.test(value)) return callback(new Error('手机号格式不正确'))
      callback()
    }
    const validatePassword = (rule, value, callback) => {
      if (!value) return callback(new Error('请输入密码'))
      if (value.length < 6) return callback(new Error('密码长度不能少于6位'))
      callback()
    }
    const validateConfirmPassword = (rule, value, callback) => {
      if (!value) return callback(new Error('请再次输入密码'))
      if (value !== this.registerForm.password) return callback(new Error('两次输入密码不一致'))
      callback()
    }

    return {
      activeTab: 'login',
      loginMode: 'password',

      passwordLoginLoading: false,
      smsLoginLoading: false,
      registerLoading: false,

      loginSmsCountdown: 0,
      registerSmsCountdown: 0,
      loginSmsTimer: null,
      registerSmsTimer: null,

      passwordLoginForm: {
        phone: '',
        password: '',
      },
      smsLoginForm: {
        phone: '',
        sms_code: '',
      },
      registerForm: {
        phone: '',
        password: '',
        confirmPassword: '',
        sms_code: '',
      },

      passwordLoginRules: {
        phone: [{ validator: validatePhone, trigger: 'blur' }],
        password: [{ validator: validatePassword, trigger: 'blur' }],
      },
      smsLoginRules: {
        phone: [{ validator: validatePhone, trigger: 'blur' }],
        sms_code: [{ required: true, message: '请输入短信验证码', trigger: 'blur' }],
      },
      registerRules: {
        phone: [{ validator: validatePhone, trigger: 'blur' }],
        password: [{ validator: validatePassword, trigger: 'blur' }],
        confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }],
      },
    }
  },
  beforeDestroy() {
    this.clearCountdown('login')
    this.clearCountdown('register')
  },
  methods: {
    saveLoginState(user) {
      localStorage.setItem('user', JSON.stringify(user))
      localStorage.setItem('token', 'mock-token')
    },
    startCountdown(scene) {
      const key = scene === 'login' ? 'loginSmsCountdown' : 'registerSmsCountdown'
      const timerKey = scene === 'login' ? 'loginSmsTimer' : 'registerSmsTimer'

      this.clearCountdown(scene)
      this[key] = 60
      this[timerKey] = setInterval(() => {
        if (this[key] <= 1) {
          this.clearCountdown(scene)
          return
        }
        this[key] -= 1
      }, 1000)
    },
    clearCountdown(scene) {
      const timerKey = scene === 'login' ? 'loginSmsTimer' : 'registerSmsTimer'
      const key = scene === 'login' ? 'loginSmsCountdown' : 'registerSmsCountdown'
      if (this[timerKey]) {
        clearInterval(this[timerKey])
        this[timerKey] = null
      }
      this[key] = 0
    },
    async requestSmsCode(phone, purpose, scene) {
      if (!PHONE_REG.test(phone || '')) {
        this.$message.warning('请输入正确的手机号码')
        return
      }
      try {
        const res = await authAPI.sendSMSCode({ phone, purpose })
        if (res.data?.success) {
          this.startCountdown(scene)
          const debugCode = res.data?.data?.debug_code
          this.$message.success(debugCode ? `验证码已发送（开发验证码：${debugCode}）` : '验证码已发送')
        } else {
          this.$message.error(res.data?.message || '验证码发送失败')
        }
      } catch (error) {
        this.$message.error(error?.response?.data?.message || '验证码发送失败')
      }
    },
    sendLoginSmsCode() {
      this.requestSmsCode(this.smsLoginForm.phone, 'login', 'login')
    },
    sendRegisterSmsCode() {
      this.requestSmsCode(this.registerForm.phone, 'register', 'register')
    },
    async handlePasswordLogin() {
      try {
        await this.$refs.passwordLoginFormRef.validate()
        this.passwordLoginLoading = true
        const response = await authAPI.loginByPassword({
          phone: this.passwordLoginForm.phone,
          password: this.passwordLoginForm.password,
        })
        if (response.data?.success) {
          this.saveLoginState(response.data.data.user)
          this.$message.success('登录成功')
          this.$router.push('/invoice')
          return
        }
        this.$message.error(response.data?.message || '登录失败')
      } catch (error) {
        this.$message.error(error?.response?.data?.message || '登录失败')
      } finally {
        this.passwordLoginLoading = false
      }
    },
    async handleSMSLogin() {
      try {
        await this.$refs.smsLoginFormRef.validate()
        this.smsLoginLoading = true
        const response = await authAPI.loginBySMS(this.smsLoginForm)
        if (response.data?.success) {
          this.saveLoginState(response.data.data.user)
          this.$message.success('登录成功')
          this.$router.push('/invoice')
          return
        }
        this.$message.error(response.data?.message || '登录失败')
      } catch (error) {
        this.$message.error(error?.response?.data?.message || '登录失败')
      } finally {
        this.smsLoginLoading = false
      }
    },
    async handleRegister() {
      try {
        await this.$refs.registerFormRef.validate()
        this.registerLoading = true
        const payload = {
          phone: this.registerForm.phone,
          password: this.registerForm.password,
          sms_code: this.registerForm.sms_code || undefined,
        }
        const response = await authAPI.register(payload)
        if (response.data?.success) {
          this.$message.success('注册成功，请登录')
          this.activeTab = 'login'
          this.loginMode = 'password'
          this.passwordLoginForm.phone = this.registerForm.phone
          this.passwordLoginForm.password = ''
          this.registerForm.password = ''
          this.registerForm.confirmPassword = ''
          return
        }
        this.$message.error(response.data?.message || '注册失败')
      } catch (error) {
        this.$message.error(error?.response?.data?.message || '注册失败')
      } finally {
        this.registerLoading = false
      }
    },
  },
}
</script>

<style scoped lang="scss">
// 基础变量
$primary: #4f46e5;
$primary-light: #818cf8;
$accent: #06b6d4;
$text-main: #1e293b;
$text-light: #64748b;
$radius: 16px;

.auth-page {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background-color: #f8fafc;
  background-image: 
    radial-gradient(at 0% 0%, rgba($primary-light, 0.15) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba($accent, 0.15) 0px, transparent 50%);
}

// 动态背景球
.bg-decoration {
  position: absolute;
  inset: 0;
  z-index: 1;
  .glow-sphere {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.6;
    animation: float-around 20s infinite alternate ease-in-out;
  }
  .sphere-1 { width: 400px; height: 400px; background: $primary-light; top: -100px; right: -50px; }
  .sphere-2 { width: 350px; height: 350px; background: $accent; bottom: -80px; left: -50px; animation-delay: -5s; }
  .sphere-3 { width: 250px; height: 250px; background: #f472b6; top: 40%; left: 20%; animation-duration: 15s; }
}

.auth-shell {
  position: relative;
  z-index: 10;
  width: 1000px;
  max-width: 95vw;
  display: grid;
  grid-template-columns: 420px 1fr;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 24px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  animation: slide-up 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}

// 左侧面板
.brand-panel {
  background: linear-gradient(135deg, $primary 0%, #312e81 100%);
  padding: 60px 45px;
  color: white;
  display: flex;
  flex-direction: column;
  justify-content: center;

  .brand-badge {
    display: inline-block;
    padding: 6px 14px;
    background: rgba(255, 255, 255, 0.15);
    border-radius: 30px;
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 24px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  h1 {
    font-size: 48px;
    font-weight: 800;
    margin-bottom: 20px;
    letter-spacing: -1px;
    background: linear-gradient(to bottom, #fff, rgba(255,255,255,0.7));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .brand-desc p {
    font-size: 16px;
    line-height: 1.6;
    color: rgba(255, 255, 255, 0.8);
    margin-bottom: 40px;
  }

  .feature-list {
    list-style: none;
    padding: 0;
    li {
      margin-bottom: 16px;
      display: flex;
      align-items: center;
      font-size: 15px;
      color: rgba(255, 255, 255, 0.9);
      i { margin-right: 12px; color: $accent; font-size: 18px; }
    }
  }
}

// 右侧表单面板
.form-panel {
  padding: 50px 60px;
  background: white;

  .panel-head {
    margin-bottom: 30px;
    h2 { font-size: 30px; color: $text-main; font-weight: 700; margin: 0; }
    .subtitle { color: $text-light; margin-top: 8px; font-size: 14px; }
  }
}

// Tabs & Radio 美化
.auth-tabs {
  ::v-deep .el-tabs__nav-wrap::after { display: none; }
  ::v-deep .el-tabs__active-bar {
    height: 3px;
    border-radius: 3px;
    background-color: $primary;
  }
  ::v-deep .el-tabs__item {
    font-size: 16px;
    height: 50px;
    line-height: 50px;
    &.is-active { color: $primary; font-weight: 700; }
  }
}

.mode-switch-wrapper {
  margin: 20px 0 25px;
  text-align: center;
  .custom-radio {
    ::v-deep .el-radio-button__inner {
      border: none;
      background: #f1f5f9;
      margin: 0 4px;
      border-radius: 8px !important;
      color: $text-light;
      font-size: 13px;
      transition: all 0.3s;
    }
    ::v-deep .el-radio-button__orig-radio:checked + .el-radio-button__inner {
      background: white;
      color: $primary;
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
  }
}

// 表单元素动效
.animated-form {
  ::v-deep .el-input__inner {
    height: 50px;
    border-radius: $radius;
    border: 1.5px solid #e2e8f0;
    padding-left: 45px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    
    &:focus {
      border-color: $primary;
      box-shadow: 0 0 0 4px rgba($primary, 0.1);
      transform: translateY(-1px);
    }
  }

  ::v-deep .el-input__prefix {
    left: 15px;
    font-size: 18px;
    color: $text-light;
  }

  ::v-deep .el-input-group__append {
    background-color: transparent;
    border: none;
    padding: 0 10px;
    .code-btn {
      color: $primary;
      font-weight: 600;
      border-left: 1.5px solid #e2e8f0;
      border-radius: 0;
      &:hover { color: $primary-light; }
    }
  }
}

// 渐变按钮动效
.gradient-btn {
  width: 100%;
  height: 52px;
  border-radius: $radius;
  border: none;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 1px;
  margin-top: 10px;
  background: linear-gradient(135deg, $primary, $primary-light);
  background-size: 200% auto;
  box-shadow: 0 10px 20px -5px rgba($primary, 0.4);
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);

  &:hover {
    background-position: right center;
    transform: translateY(-2px);
    box-shadow: 0 15px 25px -5px rgba($primary, 0.5);
  }

  &:active {
    transform: scale(0.98);
  }
}

// 动画
.form-fade-enter-active, .form-fade-leave-active {
  transition: all 0.3s ease;
}
.form-fade-enter {
  opacity: 0;
  transform: translateX(15px);
}
.form-fade-leave-to {
  opacity: 0;
  transform: translateX(-15px);
}

@keyframes float-around {
  0% { transform: translate(0, 0); }
  100% { transform: translate(30px, 40px); }
}

@keyframes slide-up {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

// 响应式优化
@media (max-width: 900px) {
  .auth-shell {
    grid-template-columns: 1fr;
    width: 450px;
  }
  .brand-panel { display: none; }
  .form-panel { padding: 40px 30px; }
}
</style>