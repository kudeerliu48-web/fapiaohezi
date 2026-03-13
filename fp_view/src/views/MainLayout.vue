<template>
  <div class="main-layout">
    <nav class="top-nav">
      <div class="nav-inner">
        <div class="nav-brand">
          <div class="brand-icon">发</div>
          <span class="brand-text">发票盒子</span>
        </div>

        <div class="nav-links">
          <router-link to="/" class="nav-link" :class="{ active: activeMenu === '/' }">
            <i class="el-icon-user" />
            <span>个人资料</span>
          </router-link>
          <router-link to="/invoice" class="nav-link" :class="{ active: activeMenu === '/invoice' }">
            <i class="el-icon-document" />
            <span>发票工作台</span>
          </router-link>
          <router-link to="/recharge" class="nav-link" :class="{ active: activeMenu === '/recharge' }">
            <i class="el-icon-wallet" />
            <span>充值</span>
          </router-link>
        </div>

        <div class="nav-right" v-if="currentUser">
          <span class="user-badge">
            <i class="el-icon-mobile-phone" />
            {{ currentUser.phone || currentUser.username }}
          </span>
          <button class="logout-btn" @click="handleLogout">
            <i class="el-icon-switch-button" />
            <span>退出</span>
          </button>
        </div>
      </div>
    </nav>

    <div class="main-content">
      <router-view />
    </div>
  </div>
</template>

<script>
export default {
  name: 'MainLayout',
  data() {
    return {
      currentUser: null,
    }
  },
  computed: {
    activeMenu() {
      return this.$route.path
    },
  },
  created() {
    this.checkUser()
  },
  methods: {
    checkUser() {
      const user = localStorage.getItem('user')
      if (user) {
        this.currentUser = JSON.parse(user)
      }
    },
    handleLogout() {
      this.$confirm('确定要退出登录吗？', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning',
      }).then(() => {
        localStorage.removeItem('user')
        localStorage.removeItem('token')
        this.$router.push('/login')
        this.$message.success('已退出登录')
      })
    },
  },
}
</script>

<style lang="scss" scoped>
$primary: #4f46e5;
$primary-light: #818cf8;
$accent: #06b6d4;
$text-main: #1e293b;
$text-light: #64748b;

.main-layout {
  min-height: 100vh;
  background-color: #f8fafc;
  background-image:
    radial-gradient(at 0% 0%, rgba($primary-light, 0.08) 0px, transparent 50%),
    radial-gradient(at 100% 100%, rgba($accent, 0.06) 0px, transparent 50%);
}

.top-nav {
  background: linear-gradient(135deg, $primary 0%, #312e81 100%);
  box-shadow: 0 4px 24px rgba(79, 70, 229, 0.25);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-inner {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  padding: 0 28px;
  height: 60px;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-right: 36px;

  .brand-icon {
    width: 34px;
    height: 34px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.2);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.15);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 16px;
    font-weight: 700;
    color: white;
  }

  .brand-text {
    font-size: 18px;
    font-weight: 700;
    color: white;
    letter-spacing: 0.5px;
  }
}

.nav-links {
  display: flex;
  gap: 4px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  border-radius: 10px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  transition: all 0.25s ease;

  i { font-size: 16px; }

  &:hover {
    color: white;
    background: rgba(255, 255, 255, 0.1);
  }

  &.active {
    color: white;
    background: rgba(255, 255, 255, 0.18);
    font-weight: 600;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
}

.nav-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 14px;

  .user-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 14px;
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.12);
    color: rgba(255, 255, 255, 0.9);
    font-size: 13px;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  .logout-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 6px 14px;
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    background: rgba(255, 255, 255, 0.08);
    color: rgba(255, 255, 255, 0.8);
    font-size: 13px;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      background: rgba(255, 255, 255, 0.18);
      color: white;
      border-color: rgba(255, 255, 255, 0.3);
    }
  }
}

.main-content {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
  animation: content-fade 0.4s ease-out;
}

// 统一内容区域内输入框边框为 1px
.main-content ::v-deep .el-input__inner {
  border-width: 1px;
}

@keyframes content-fade {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .nav-inner { padding: 0 16px; }
  .nav-brand { margin-right: 16px; }
  .brand-text { display: none; }
  .nav-link span { display: none; }
  .nav-link { padding: 8px 12px; }
  .user-badge span { display: none; }
  .main-content { padding: 16px; }
}
</style>
