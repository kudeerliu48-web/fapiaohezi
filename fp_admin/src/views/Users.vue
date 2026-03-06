<template>
  <div class="users-page">
    <el-card>
      <div slot="header" class="page-header">
        <span>用户列表</span>
      </div>
      
      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索用户名或邮箱"
          style="width: 300px;"
          clearable
          @keyup.enter.native="handleSearch"
        >
          <el-button slot="append" icon="el-icon-search" @click="handleSearch">搜索</el-button>
        </el-input>
      </div>
      
      <!-- 用户表格 -->
      <el-table
        :data="userList"
        v-loading="loading"
        stripe
        border
        size="small"
        style="width: 100%"
      >
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="id" label="ID" width="200" show-overflow-tooltip />
        <el-table-column prop="username" label="用户名" width="150" show-overflow-tooltip />
        <el-table-column prop="email" label="邮箱" width="200" show-overflow-tooltip />
        <el-table-column prop="company" label="公司" width="200" show-overflow-tooltip />
        <el-table-column prop="phone" label="电话" width="150" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template slot-scope="scope">
            <el-tag :type="scope.row.status === 1 ? 'success' : 'danger'">
              {{ scope.row.status === 1 ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="注册时间" width="180">
          <template slot-scope="scope">
            {{ formatDateTime(scope.row.register_time) }}
          </template>
        </el-table-column>
        <el-table-column label="最后登录时间" width="180">
          <template slot-scope="scope">
            {{ formatDateTime(scope.row.last_login_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="150">
          <template slot-scope="scope">
            <el-button
              type="primary"
              size="small"
              @click="handleViewDetail(scope.row)"
            >
              详情
            </el-button>
            <el-button
              type="danger"
              size="small"
              @click="handleDelete(scope.row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          :current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
    
    <!-- 用户详情对话框 -->
    <el-dialog
      title="用户详情"
      :visible.sync="detailDialogVisible"
      width="600px"
    >
      <el-descriptions :column="2" border v-if="currentUser">
        <el-descriptions-item label="用户 ID">{{ currentUser.id }}</el-descriptions-item>
        <el-descriptions-item label="用户名">{{ currentUser.username }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ currentUser.email }}</el-descriptions-item>
        <el-descriptions-item label="电话">{{ currentUser.phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="公司">{{ currentUser.company || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="currentUser.status === 1 ? 'success' : 'danger'" size="small">
            {{ currentUser.status === 1 ? '正常' : '禁用' }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="注册时间">{{ currentUser.register_time }}</el-descriptions-item>
        <el-descriptions-item label="最后登录时间">{{ currentUser.last_login_time || '-' }}</el-descriptions-item>
        <el-descriptions-item label="角色">
          <el-tag size="small">{{ currentUser.role || 'user' }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <span slot="footer" class="dialog-footer">
        <el-button @click="detailDialogVisible = false">关 闭</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import { getUsersList, getUserDetail, deleteUser } from '@/api/user'

export default {
  name: 'Users',
  data() {
    return {
      userList: [],
      loading: false,
      searchKeyword: '',
      currentPage: 1,
      pageSize: 10,
      total: 0,
      detailDialogVisible: false,
      currentUser: null
    }
  },
  
  created() {
    this.fetchUsers()
  },
  
  methods: {
    async fetchUsers() {
      this.loading = true
      try {
        const res = await getUsersList(this.currentPage, this.pageSize)
        if (res.success) {
          this.userList = res.data.users || []
          this.total = res.data.total || 0
        }
      } catch (error) {
        console.error('获取用户列表失败:', error)
      } finally {
        this.loading = false
      }
    },
    
    handleSearch() {
      this.currentPage = 1
      this.fetchUsers()
    },
    
    handleSizeChange(val) {
      this.pageSize = val
      this.fetchUsers()
    },
    
    handleCurrentChange(val) {
      this.currentPage = val
      this.fetchUsers()
    },
    
    async handleViewDetail(row) {
      try {
        const res = await getUserDetail(row.id)
        if (res.success) {
          this.currentUser = res.data
          this.detailDialogVisible = true
        }
      } catch (error) {
        console.error('获取用户详情失败:', error)
      }
    },
    
    handleDelete(row) {
      this.$confirm('确定要删除该用户吗？此操作不可恢复', '提示', {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }).then(async () => {
        try {
          const res = await deleteUser(row.id)
          if (res.success) {
            this.$message.success('删除成功')
            this.fetchUsers()
          }
        } catch (error) {
          console.error('删除失败:', error)
        }
      }).catch(() => {})
    },

    formatDateTime(val) {
      if (!val) return '-'
      const s = String(val).replace('T', ' ')
      return s.length >= 19 ? s.slice(0, 19) : s
    }
  }
}
</script>

<style scoped lang="scss">
.users-page {
  .page-header {
    font-size: 16px;
    font-weight: bold;
  }
  
  .search-bar {
    margin-bottom: 20px;
  }
  
  .pagination-container {
    margin-top: 20px;
    text-align: right;
  }

  /* 表格紧凑 + 文本省略号 + 显示格线 */
  ::v-deep .el-table {
    font-size: 13px;
    border: 1px solid #ebeef5;
    
    // 网格边框增强
    th.el-table__cell,
    td.el-table__cell {
      border: 1px solid #EBEEF5;
    }
    
    th.el-table__cell {
      background-color: #F5F7FA;
      color: #606266;
      font-weight: 600;
    }
    
    .el-table__body tr:hover > td {
      background-color: #ecf5ff;
    }
  }
  
  ::v-deep .el-table .cell {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
