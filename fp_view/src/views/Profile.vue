<template>
  <div class="profile-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">个人信息</h1>
        <p class="page-desc">查看并维护当前账号资料</p>
      </div>
      <el-button type="primary" icon="el-icon-edit" @click="openEditDialog">编辑信息</el-button>
    </div>

    <el-card shadow="never" class="profile-card">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="用户名">{{ userInfo.username || '-' }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ userInfo.email || '-' }}</el-descriptions-item>
        <el-descriptions-item label="公司">{{ userInfo.company || '-' }}</el-descriptions-item>
        <el-descriptions-item label="手机号">{{ userInfo.phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="注册时间">{{ formatDate(userInfo.register_time) }}</el-descriptions-item>
        <el-descriptions-item label="最近登录">{{ formatDate(userInfo.last_login_time || userInfo.login_time) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-dialog title="编辑个人信息" :visible.sync="editDialogVisible" width="480px" @close="cancelEdit">
      <el-form :model="editForm" label-width="90px">
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="公司">
          <el-input v-model="editForm.company" placeholder="请输入公司" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="editForm.phone" placeholder="请输入手机号" />
        </el-form-item>
      </el-form>
      <span slot="footer">
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
      userInfo: {},
      editDialogVisible: false,
      editForm: {
        email: '',
        company: '',
        phone: '',
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
            email: this.userInfo.email || '',
            company: this.userInfo.company || '',
            phone: this.userInfo.phone || '',
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
    },
    async saveUserInfo() {
      try {
        const user = JSON.parse(localStorage.getItem('user') || '{}')
        if (!user.id) return
        const res = await authAPI.updateUserInfo(user.id, this.editForm)
        if (res.data?.success) {
          this.$message.success('用户信息更新成功')
          this.editDialogVisible = false
          await this.loadUserInfo()
        } else {
          this.$message.error(res.data?.message || '更新失败')
        }
      } catch (error) {
        this.$message.error('更新用户信息失败')
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
.profile-page {
  .page-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
  }
  .page-title {
    margin: 0;
    font-size: 22px;
  }
  .page-desc {
    margin: 6px 0 0;
    color: #909399;
    font-size: 13px;
  }
}
</style>
