<template>
  <div class="profile-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">个人资料</h1>
        <p class="page-desc">手机号为登录账号，邮箱与公司可在此维护</p>
      </div>
      <button class="edit-btn" @click="openEditDialog">
        <i class="el-icon-edit" />
        编辑资料
      </button>
    </div>

    <div class="profile-card">
      <div class="card-inner">
        <div class="avatar-section">
          <div class="avatar">
            <i class="el-icon-user" />
          </div>
          <div class="user-name">{{ userInfo.phone || userInfo.username || '未设置' }}</div>
          <div class="user-role">{{ userInfo.role || 'user' }}</div>
        </div>

        <div class="info-grid">
          <div class="info-item">
            <div class="info-icon"><i class="el-icon-mobile-phone" /></div>
            <div class="info-body">
              <div class="info-label">手机号码</div>
              <div class="info-value">{{ userInfo.phone || userInfo.username || '-' }}</div>
            </div>
          </div>
          <div class="info-item">
            <div class="info-icon"><i class="el-icon-message" /></div>
            <div class="info-body">
              <div class="info-label">邮箱</div>
              <div class="info-value">{{ userInfo.email || '-' }}</div>
            </div>
          </div>
          <div class="info-item">
            <div class="info-icon"><i class="el-icon-office-building" /></div>
            <div class="info-body">
              <div class="info-label">公司</div>
              <div class="info-value">{{ userInfo.company || '-' }}</div>
            </div>
          </div>
          <div class="info-item">
            <div class="info-icon"><i class="el-icon-time" /></div>
            <div class="info-body">
              <div class="info-label">注册时间</div>
              <div class="info-value">{{ formatDate(userInfo.register_time) }}</div>
            </div>
          </div>
          <div class="info-item">
            <div class="info-icon"><i class="el-icon-circle-check" /></div>
            <div class="info-body">
              <div class="info-label">最近登录</div>
              <div class="info-value">{{ formatDate(userInfo.last_login_time || userInfo.login_time) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-dialog title="编辑个人资料" :visible.sync="editDialogVisible" width="480px" custom-class="profile-dialog" @close="cancelEdit">
      <el-form ref="editFormRef" :model="editForm" :rules="rules" label-width="90px">
        <el-form-item label="手机号码" prop="phone">
          <el-input v-model.trim="editForm.phone" placeholder="请输入手机号" prefix-icon="el-icon-mobile-phone" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model.trim="editForm.email" placeholder="请输入邮箱（选填）" prefix-icon="el-icon-message" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model.trim="editForm.company" placeholder="请输入公司（选填）" prefix-icon="el-icon-office-building" />
        </el-form-item>
      </el-form>
      <span slot="footer">
        <el-button @click="cancelEdit">取消</el-button>
        <el-button type="primary" class="save-btn" @click="saveUserInfo">保存</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import { authAPI } from '@/api/auth'

const PHONE_REG = /^1\d{10}$/

export default {
  name: 'Profile',
  data() {
    return {
      userInfo: {},
      editDialogVisible: false,
      editForm: {
        phone: '',
        email: '',
        company: '',
      },
      rules: {
        phone: [
          { required: true, message: '请输入手机号码', trigger: 'blur' },
          {
            validator: (rule, value, callback) => {
              if (!PHONE_REG.test(value || '')) {
                callback(new Error('手机号格式不正确'))
                return
              }
              callback()
            },
            trigger: 'blur',
          },
        ],
        email: [{ type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
      },
    }
  },
  async mounted() {
    await this.loadUserInfo()
  },
  methods: {
    async loadUserInfo() {
      try {
        const user = JSON.parse(localStorage.getItem('user') || '{}')
        if (!user.id) return
        const res = await authAPI.getUserInfo(user.id)
        if (res.data?.success) {
          this.userInfo = res.data.data || {}
          this.editForm = {
            phone: this.userInfo.phone || this.userInfo.username || '',
            email: this.userInfo.email || '',
            company: this.userInfo.company || '',
          }
        }
      } catch (error) {
        this.$message.error('获取用户信息失败')
      }
    },
    openEditDialog() {
      this.editDialogVisible = true
    },
    cancelEdit() {
      this.editDialogVisible = false
      this.$nextTick(() => {
        this.$refs.editFormRef?.clearValidate()
      })
    },
    async saveUserInfo() {
      try {
        await this.$refs.editFormRef.validate()
        const user = JSON.parse(localStorage.getItem('user') || '{}')
        if (!user.id) return

        const payload = {
          phone: this.editForm.phone,
          email: this.editForm.email || undefined,
          company: this.editForm.company || undefined,
        }
        const res = await authAPI.updateUserInfo(user.id, payload)
        if (res.data?.success) {
          this.$message.success('用户资料更新成功')
          this.editDialogVisible = false
          await this.loadUserInfo()

          const cached = JSON.parse(localStorage.getItem('user') || '{}')
          cached.phone = this.userInfo.phone || this.userInfo.username
          cached.username = this.userInfo.username
          cached.email = this.userInfo.email
          cached.company = this.userInfo.company
          localStorage.setItem('user', JSON.stringify(cached))
        } else {
          this.$message.error(res.data?.message || '更新失败')
        }
      } catch (error) {
        if (error?.message) {
          this.$message.error(error.message)
        }
      }
    },
    formatDate(value) {
      if (!value) return '-'
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return String(value)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    },
  },
}
</script>

<style scoped lang="scss">
$primary: #4f46e5;
$primary-light: #818cf8;
$accent: #06b6d4;
$text-main: #1e293b;
$text-light: #64748b;
$radius: 16px;

.profile-page {
  max-width: 800px;
  margin: 0 auto;
  animation: profile-enter 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: $text-main;
  letter-spacing: -0.5px;
}

.page-desc {
  margin: 6px 0 0;
  color: $text-light;
  font-size: 14px;
}

.edit-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 22px;
  border-radius: 12px;
  border: none;
  font-size: 14px;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, $primary, $primary-light);
  box-shadow: 0 8px 20px -4px rgba($primary, 0.35);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 28px -4px rgba($primary, 0.45);
  }

  &:active {
    transform: scale(0.97);
  }
}

.profile-card {
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 20px 40px -12px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.card-inner {
  padding: 40px;
}

.avatar-section {
  text-align: center;
  margin-bottom: 36px;
  padding-bottom: 32px;
  border-bottom: 1px solid #f1f5f9;

  .avatar {
    width: 80px;
    height: 80px;
    border-radius: 20px;
    background: linear-gradient(135deg, $primary, #312e81);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 16px;
    box-shadow: 0 10px 24px -6px rgba($primary, 0.4);

    i {
      font-size: 36px;
      color: white;
    }
  }

  .user-name {
    font-size: 22px;
    font-weight: 700;
    color: $text-main;
    margin-bottom: 4px;
  }

  .user-role {
    display: inline-block;
    padding: 3px 14px;
    border-radius: 20px;
    background: rgba($primary, 0.08);
    color: $primary;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.5px;
  }
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  border-radius: 14px;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  transition: all 0.25s ease;

  &:hover {
    background: white;
    border-color: rgba($primary, 0.15);
    box-shadow: 0 6px 16px rgba($primary, 0.06);
    transform: translateY(-1px);
  }

  .info-icon {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: linear-gradient(135deg, rgba($primary, 0.1), rgba($primary-light, 0.08));
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;

    i {
      font-size: 18px;
      color: $primary;
    }
  }

  .info-label {
    font-size: 12px;
    color: $text-light;
    margin-bottom: 2px;
  }

  .info-value {
    font-size: 15px;
    font-weight: 600;
    color: $text-main;
    word-break: break-all;
  }
}

// Dialog 样式
::v-deep .profile-dialog {
  border-radius: 20px;
  overflow: hidden;

  .el-dialog__header {
    background: linear-gradient(135deg, $primary, #312e81);
    padding: 20px 24px;

    .el-dialog__title {
      color: white;
      font-weight: 700;
      font-size: 18px;
    }

    .el-dialog__headerbtn .el-dialog__close {
      color: rgba(255, 255, 255, 0.7);
      &:hover { color: white; }
    }
  }

  .el-dialog__body {
    padding: 28px 24px;
  }

  .el-input__inner {
    height: 44px;
    border-radius: 12px;
    border: 1.5px solid #e2e8f0;
    transition: all 0.3s ease;

    &:focus {
      border-color: $primary;
      box-shadow: 0 0 0 3px rgba($primary, 0.1);
    }
  }
}

.save-btn {
  border-radius: 12px;
  background: linear-gradient(135deg, $primary, $primary-light);
  border: none;
  font-weight: 600;
  padding: 10px 28px;
  box-shadow: 0 6px 16px rgba($primary, 0.3);

  &:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba($primary, 0.4);
  }
}

@keyframes profile-enter {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .card-inner { padding: 24px; }
  .info-grid { grid-template-columns: 1fr; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 16px; }
}
</style>
