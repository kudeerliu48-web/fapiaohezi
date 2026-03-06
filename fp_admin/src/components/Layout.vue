<template>
  <el-container class="layout-container">
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <h2>发票盒子</h2>
      </div>
      <el-menu
        :default-active="$route.path"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <el-menu-item index="/dashboard">
          <i class="el-icon-s-home"></i>
          <span slot="title">首页</span>
        </el-menu-item>
        <el-menu-item index="/users">
          <i class="el-icon-user"></i>
          <span slot="title">用户管理</span>
        </el-menu-item>
        <el-menu-item index="/invoices">
          <i class="el-icon-document"></i>
          <span slot="title">发票管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header class="header">
        <div class="header-title">{{ $route.meta.title || '发票管理系统' }}</div>
        <div class="header-info">
          <span>管理员</span>
        </div>
      </el-header>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script>
export default {
  name: 'Layout'
}
</script>

<style scoped lang="scss">
.layout-container {
  height: 100vh;
  
  .sidebar {
    background-color: #304156;
    
    .logo {
      height: 60px;
      line-height: 60px;
      text-align: center;
      color: #fff;
      font-size: 20px;
      font-weight: bold;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .el-menu {
      border-right: none;
    }
  }
  
  .header {
    background: #fff;
    border-bottom: 1px solid #e6e6e6;
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0 20px;
    
    .header-title {
      font-size: 18px;
      font-weight: bold;
    }
    
    .header-info {
      color: #666;
    }
  }
  
  .main-content {
    background: #f0f2f5;
    padding: 20px;
  }
}
</style>
