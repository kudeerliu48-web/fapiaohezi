<template>
  <div class="main-layout">
    <!-- 顶部导航栏 -->
    <el-menu
      :default-active="activeMenu"
      mode="horizontal"
      background-color="#545c64"
      text-color="#fff"
      active-text-color="#ffd04b"
      router
      class="top-menu"
    >
      <el-menu-item index="/">
        <i class="el-icon-user"></i>
        <span slot="title">个人信息</span>
      </el-menu-item>
      <el-menu-item index="/invoice">
        <i class="el-icon-document"></i>
        <span slot="title">发票整理</span>
      </el-menu-item>
      
      <div class="right-menu">
        <span class="user-info" v-if="currentUser">
          <i class="el-icon-avatar"></i>
          {{ currentUser.username }}
        </span>
        <el-button type="text" @click="handleLogout" v-if="currentUser">
          <i class="el-icon-switch-button"></i> 退出
        </el-button>
      </div>
    </el-menu>

    <!-- 主内容区 -->
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
      currentUser: null
    }
  },
  computed: {
    activeMenu() {
      return this.$route.path
    }
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
        type: 'warning'
      }).then(() => {
        localStorage.removeItem('user')
        localStorage.removeItem('token')
        this.$router.push('/login')
        this.$message.success('已退出登录')
      })
    }
  }
}
</script>

<style lang="scss" scoped>
.main-layout {
  min-height: 100vh;
  background-color: #f0f2f5;
}

.top-menu {
  display: flex;
  justify-content: space-between;
  
  .right-menu {
    margin-left: auto;
    display: flex;
    align-items: center;
    
    .user-info {
      color: #fff;
      margin-right: 20px;
      font-size: 14px;
    }
    
    ::v-deep .el-button--text {
      color: #ffd04b;
    }
  }
}

.main-content {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
