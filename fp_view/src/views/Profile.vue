<template>
  <div class="profile-page">
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">个人信息</h1>
        <p class="page-desc">您的账户信息</p>
      </div>
      <el-button type="primary" icon="el-icon-edit" class="btn-edit" @click="openEditDialog">
        修改
      </el-button>
    </div>

    <div class="profile-body">
      <div class="avatar-section">
        <div class="avatar-box">
          <span class="avatar-text">{{ userInitial }}</span>
        </div>
      </div>

      <div class="info-cards">
        <div class="info-card card-name">
          <span class="card-label">用户名</span>
          <span class="card-value">{{ userInfo.username }}</span>
        </div>
        <div class="info-card card-email">
          <span class="card-label">邮箱</span>
          <span class="card-value">{{ userInfo.email }}</span>
        </div>
        <div class="info-card card-company">
          <span class="card-label">公司</span>
          <span class="card-value">{{ userInfo.company || '未填写' }}</span>
        </div>
        <div class="info-card card-phone">
          <span class="card-label">手机号码</span>
          <span class="card-value">{{ userInfo.phone || '未填写' }}</span>
        </div>
        <div class="info-card card-register">
          <span class="card-label">注册时间</span>
          <span class="card-value">{{ formattedRegisterTime }}</span>
        </div>
        <div class="info-card card-login">
          <span class="card-label">最后登录</span>
          <span class="card-value">{{ formattedLastLoginTime }}</span>
        </div>
      </div>
    </div>

    <!-- 修改弹窗 -->
    <el-dialog
      title="修改个人信息"
      :visible.sync="editDialogVisible"
      width="480px"
      class="edit-dialog"
      :append-to-body="true"
      :lock-scroll="true"
      @close="cancelEdit"
    >
      <el-form :model="editForm" label-width="90px" label-position="left">
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="editForm.company" placeholder="请输入公司" />
        </el-form-item>
        <el-form-item label="手机号码">
          <el-input v-model="editForm.phone" placeholder="请输入手机号码" />
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="cancelEdit">取消</el-button>
        <el-button type="primary" @click="saveUserInfo">保存</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import { authAPI } from '@/api/auth'

export default {
  name: 'Profile',
  data() {
    return {
      userInfo: {
        username: '',
        email: '',
        company: '',
        phone: '',
        registerTime: '',
        lastLoginTime: ''
      },
      editDialogVisible: false,
      editForm: {
        email: '',
        company: '',
        phone: ''
      },
      loading: false
    }
  },
  computed: {
    userInitial() {
      return this.userInfo.username ? this.userInfo.username.charAt(0) : '用'
    },
    formattedRegisterTime() {
      return this.formatDate(this.userInfo.registerTime)
    },
    formattedLastLoginTime() {
      return this.formatDate(this.userInfo.lastLoginTime)
    }
  },
  async mounted() {
    await this.loadUserInfo()
  },
  methods: {
    async loadUserInfo() {
      try {
        this.loading = true
        const user = JSON.parse(localStorage.getItem('user'))
        
        if (user) {
          const response = await authAPI.getUserInfo(user.id)
          
          if (response.data.success) {
            this.userInfo = response.data.data
            this.editForm = {
              email: this.userInfo.email,
              company: this.userInfo.company,
              phone: this.userInfo.phone
            }
          }
        }
      } catch (error) {
        console.error('获取用户信息失败:', error)
        this.$message.error('获取用户信息失败')
      } finally {
        this.loading = false
      }
    },
    
    openEditDialog() {
      this.editDialogVisible = true
    },
    
    cancelEdit() {
      this.editDialogVisible = false
    },
    
    async saveUserInfo() {
      try {
        const user = JSON.parse(localStorage.getItem('user'))
        
        const response = await authAPI.updateUserInfo(user.id, this.editForm)
        
        if (response.data.success) {
          this.$message.success('用户信息更新成功')
          this.editDialogVisible = false
          
          // 重新加载用户信息
          await this.loadUserInfo()
        }
      } catch (error) {
        console.error('更新用户信息失败:', error)
        this.$message.error('更新用户信息失败')
      }
    },
    
    formatDate(dateString) {
      if (!dateString) return '暂无'
      
      const date = new Date(dateString)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.profile-page {
  min-height: 100%;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 40px;
  flex-wrap: wrap;
  gap: 20px;
  .header-left {
    .page-title {
      font-size: 28px;
      font-weight: 800;
      background: linear-gradient(135deg, #6366f1, #8b5cf6);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 8px;
      letter-spacing: -0.5px;
    }
    .page-desc {
      font-size: 15px;
      color: #64748b;
      font-weight: 400;
    }
  }
  .btn-edit {
    border-radius: 12px;
    padding: 12px 24px;
    font-weight: 600;
    font-size: 15px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border: none;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 8px 20px rgba(99, 102, 241, 0.3);
    }
  }
}

.profile-body {
  .avatar-section {
    position: relative;
    display: flex;
    justify-content: center;
    margin-bottom: 32px;
  }

  .avatar-box {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    border: 2px solid rgba(255, 255, 255, 0.9);
    transition: all 0.2s ease;
    &:hover {
      transform: scale(1.02);
      box-shadow: 0 6px 16px rgba(99, 102, 241, 0.4);
    }
    .avatar-text {
      font-size: 28px;
      font-weight: 700;
      color: #fff;
      text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
    }
  }
}

.info-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.info-card {
  position: relative;
  padding: 20px 24px;
  border-radius: 16px;
  overflow: hidden;
  min-height: 80px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  transition: all 0.2s ease;
  cursor: pointer;
  border: 1px solid rgba(0, 0, 0, 0.06);
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
  }
  .card-label {
    font-size: 13px;
    color: #64748b;
    margin-bottom: 6px;
    position: relative;
    z-index: 1;
    font-weight: 500;
  }
  .card-value {
    font-size: 16px;
    font-weight: 600;
    color: #1a1a2e;
    position: relative;
    z-index: 1;
  }
}

.card-name { 
  border-left: 4px solid #f59e0b;
  &:hover {
    box-shadow: 0 8px 20px rgba(245, 158, 11, 0.15);
  }
}

.card-gender { 
  border-left: 4px solid #ec4899;
  &:hover {
    box-shadow: 0 8px 20px rgba(236, 72, 153, 0.15);
  }
}

.card-email { 
  border-left: 4px solid #3b82f6;
  &:hover {
    box-shadow: 0 8px 20px rgba(59, 130, 246, 0.15);
  }
}

.card-company { 
  border-left: 4px solid #10b981;
  &:hover {
    box-shadow: 0 8px 20px rgba(16, 185, 129, 0.15);
  }
}

.card-phone { 
  border-left: 4px solid #8b5cf6;
  &:hover {
    box-shadow: 0 8px 20px rgba(139, 92, 246, 0.15);
  }
}

.card-register { 
  border-left: 4px solid #10b981;
  &:hover {
    box-shadow: 0 8px 20px rgba(16, 185, 129, 0.15);
  }
}

.card-login { 
  border-left: 4px solid #f59e0b;
  &:hover {
    box-shadow: 0 8px 20px rgba(245, 158, 11, 0.15);
  }
}
</style>
