<template>
  <div class="login-container">
    <el-card class="login-card" shadow="always">
      <div class="title-wrap">
        <h1>发票盒子</h1>
        <p>登录后进入发票工作台</p>
      </div>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="登录" name="login">
          <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" @submit.native.prevent>
            <el-form-item prop="username">
              <el-input v-model="loginForm.username" placeholder="请输入用户名" prefix-icon="el-icon-user" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="请输入密码"
                prefix-icon="el-icon-lock"
                show-password
                @keyup.enter.native="handleLogin"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="loginLoading" style="width: 100%" @click="handleLogin">
                {{ loginLoading ? '登录中...' : '登录' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" @submit.native.prevent>
            <el-form-item prop="username">
              <el-input v-model="registerForm.username" placeholder="请输入用户名" prefix-icon="el-icon-user" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="registerForm.password" type="password" placeholder="请输入密码" prefix-icon="el-icon-lock" show-password />
            </el-form-item>
            <el-form-item prop="confirmPassword">
              <el-input v-model="registerForm.confirmPassword" type="password" placeholder="请再次输入密码" prefix-icon="el-icon-lock" show-password />
            </el-form-item>
            <el-form-item prop="email">
              <el-input v-model="registerForm.email" placeholder="请输入邮箱" prefix-icon="el-icon-message" />
            </el-form-item>
            <el-form-item prop="company">
              <el-input v-model="registerForm.company" placeholder="请输入公司（可选）" prefix-icon="el-icon-office-building" />
            </el-form-item>
            <el-form-item prop="phone">
              <el-input v-model="registerForm.phone" placeholder="请输入手机号（可选）" prefix-icon="el-icon-phone" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="registerLoading" style="width: 100%" @click="handleRegister">
                {{ registerLoading ? '注册中...' : '注册' }}
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Login',
  data() {
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
      loginLoading: false,
      registerLoading: false,
      loginForm: {
        username: '',
        password: '',
      },
      registerForm: {
        username: '',
        password: '',
        confirmPassword: '',
        email: '',
        company: '',
        phone: '',
      },
      loginRules: {
        username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
        password: [{ validator: validatePassword, trigger: 'blur' }],
      },
      registerRules: {
        username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
        password: [{ validator: validatePassword, trigger: 'blur' }],
        confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }],
        email: [
          { required: true, message: '请输入邮箱', trigger: 'blur' },
          { type: 'email', message: '邮箱格式不正确', trigger: 'blur' },
        ],
      },
    }
  },
  methods: {
    async handleLogin() {
      try {
        await this.$refs.loginFormRef.validate()
        this.loginLoading = true
        const response = await axios.post('http://localhost:8000/api/login', {
          username: this.loginForm.username,
          password: this.loginForm.password,
        })
        if (response.data?.success) {
          localStorage.setItem('user', JSON.stringify(response.data.data.user))
          localStorage.setItem('token', 'mock-token')
          this.$message.success('登录成功')
          this.$router.push('/invoice')
          return
        }
        this.$message.error(response.data?.message || '登录失败')
      } catch (error) {
        this.$message.error(error?.response?.data?.message || '登录失败')
      } finally {
        this.loginLoading = false
      }
    },
    async handleRegister() {
      try {
        await this.$refs.registerFormRef.validate()
        this.registerLoading = true
        const response = await axios.post('http://localhost:8000/api/register', {
          username: this.registerForm.username,
          password: this.registerForm.password,
          email: this.registerForm.email,
          company: this.registerForm.company,
          phone: this.registerForm.phone,
        })
        if (response.data?.success) {
          this.$message.success('注册成功，请登录')
          this.activeTab = 'login'
          this.loginForm.username = this.registerForm.username
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
.login-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.login-card {
  width: 460px;
}

.title-wrap {
  margin-bottom: 12px;
  text-align: center;
  h1 {
    margin: 0 0 4px;
    font-size: 24px;
  }
  p {
    margin: 0;
    color: #909399;
    font-size: 13px;
  }
}
</style>
