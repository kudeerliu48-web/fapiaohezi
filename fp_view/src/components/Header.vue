<template>
  <header class="app-header">
    <div class="header-content">
      <div class="header-left">
        <h1 class="app-title">发票盒子</h1>
        <p class="app-subtitle">智能发票管理系统</p>
      </div>
      <div class="header-right">
        <div class="header-actions">
          <el-button type="text" class="header-btn theme-btn" @click="toggleTheme">
            <i :class="isDark ? 'el-icon-sunny' : 'el-icon-moon'"></i>
          </el-button>
          <el-button type="text" class="header-btn" @click="showNotifications">
            <i class="el-icon-bell"></i>
            <span class="badge" v-if="notificationCount > 0">{{ notificationCount }}</span>
          </el-button>
          <el-dropdown trigger="click" @command="handleUserAction">
            <div class="user-info">
              <div class="user-avatar">
                <span class="avatar-text">{{ userInitial }}</span>
              </div>
              <div class="user-details">
                <span class="user-name">{{ userName }}</span>
                <span class="user-role">管理员</span>
              </div>
              <i class="el-icon-arrow-down user-dropdown"></i>
            </div>
            <el-dropdown-menu slot="dropdown">
              <el-dropdown-item command="profile">
                <i class="el-icon-user"></i>
                个人资料
              </el-dropdown-item>
              <el-dropdown-item command="settings">
                <i class="el-icon-setting"></i>
                账户设置
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <i class="el-icon-switch-button"></i>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </el-dropdown>
        </div>
      </div>
    </div>
  </header>
</template>

<script>
import { authAPI } from '@/api/auth'

export default {
  name: 'Header',
  data() {
    return {
      notificationCount: 3,
      isDark: false
    }
  },
  computed: {
    userName() {
      const user = JSON.parse(localStorage.getItem('user'))
      return user ? user.username : '用户'
    },
    userInitial() {
      const name = this.userName
      return name ? name.charAt(0) : '用'
    }
  },
  methods: {
    showNotifications() {
      this.$message.info('暂无新通知')
    },
    showSettings() {
      this.$message.info('设置功能开发中')
    },
    toggleTheme() {
      this.isDark = !this.isDark
      this.$message.info(this.isDark ? '切换到深色主题' : '切换到浅色主题')
    },
    handleUserAction(command) {
      switch(command) {
        case 'profile':
          this.$router.push('/')
          break
        case 'settings':
          this.$message.info('用户设置开发中')
          break
        case 'logout':
          this.handleLogout()
          break
      }
    },
    async handleLogout() {
      try {
        await this.$confirm('确定要退出登录吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        // 调用登出API
        await authAPI.logout()
        
        this.$message.success('已退出登录')
        
        // 跳转到登录页
        this.$router.push('/login')
      } catch (error) {
        if (error !== 'cancel') {
          console.error('登出失败:', error)
          this.$message.error('登出失败')
        }
      }
    }
  }
}
</script>

<style lang="scss" scoped>
.app-header {
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  width: 100%;
  left: 0;
  right: 0;
}

.header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 16.666%;
  margin-left: -8.333%;
  margin-right: -8.333%;
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}

.header-left {
  .app-title {
    font-size: 24px;
    font-weight: 800;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 4px 0;
    letter-spacing: -0.5px;
  }
  .app-subtitle {
    font-size: 14px;
    color: #64748b;
    margin: 0;
    font-weight: 400;
  }
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.1);
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  &:hover {
    background: linear-gradient(135deg, #eef2ff, #e0e7ff);
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1);
  }
  .user-dropdown {
    margin-left: 8px;
    color: #64748b;
    font-size: 12px;
    transition: transform 0.2s ease;
  }
  &:hover .user-dropdown {
    transform: translateY(2px);
  }
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  display: flex;
  align-items: center;
  justify-content: center;
  .avatar-text {
    font-size: 14px;
    font-weight: 700;
    color: #fff;
  }
}

.user-details {
  display: flex;
  flex-direction: column;
  .user-name {
    font-size: 14px;
    font-weight: 600;
    color: #334155;
    line-height: 1.2;
  }
  .user-role {
    font-size: 12px;
    color: #64748b;
    line-height: 1.2;
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-btn {
  position: relative;
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: #64748b;
  transition: all 0.2s ease;
  border: 2px solid transparent;
  &:hover {
    background: rgba(99, 102, 241, 0.1);
    color: #6366f1;
    border-color: rgba(99, 102, 241, 0.2);
  }
}

.theme-btn {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.1), rgba(139, 92, 246, 0.1));
  &:hover {
    background: linear-gradient(135deg, rgba(99, 102, 241, 0.2), rgba(139, 92, 246, 0.2));
  }
}

.badge {
  position: absolute;
  top: 6px;
  right: 6px;
  background: #ef4444;
  color: white;
  font-size: 10px;
  font-weight: 600;
  padding: 2px 5px;
  border-radius: 10px;
  min-width: 16px;
  text-align: center;
  line-height: 1;
}

@media (max-width: 768px) {
  .header-content {
    padding: 12px 20px;
  }
  
  .header-left .app-title {
    font-size: 20px;
  }
  
  .user-details {
    display: none;
  }
  
  .header-right {
    gap: 16px;
  }
}

@media (max-width: 480px) {
  .header-content {
    padding: 10px 16px;
  }
  
  .app-subtitle {
    display: none;
  }
  
  .user-info {
    padding: 8px;
  }
}
</style>
