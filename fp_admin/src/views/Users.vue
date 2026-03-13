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

        <el-button
          type="warning"
          icon="el-icon-setting"
          :disabled="selectedUsers.length === 0"
          @click="openBatchMemberDialog"
          style="margin-left: 12px;"
        >
          批量设置会员 ({{ selectedUsers.length }})
        </el-button>
      </div>
      
      <!-- 用户表格 -->
      <el-table
        :data="userList"
        v-loading="loading"
        stripe
        border
        size="small"
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" align="center" />
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
        <el-table-column prop="member_type" label="会员类型" width="110" align="center">
          <template slot-scope="scope">
            <el-tag :type="getMemberTypeTag(scope.row.member_type)" size="small">
              {{ getMemberTypeText(scope.row.member_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="会员开通时间" width="160">
          <template slot-scope="scope">
            {{ formatDateTime(scope.row.member_start_at) }}
          </template>
        </el-table-column>
        <el-table-column label="剩余时间" width="120" align="center">
          <template slot-scope="scope">
            {{ getRemainingText(scope.row) }}
          </template>
        </el-table-column>
        <el-table-column prop="recognition_used" label="已用识别次数" width="110" align="center">
          <template slot-scope="scope">
            {{ scope.row.recognition_used != null ? scope.row.recognition_used : 0 }}
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
        <el-table-column label="操作" fixed="right" width="200">
          <template slot-scope="scope">
            <el-button
              type="primary"
              size="small"
              @click="handleViewDetail(scope.row)"
            >
              详情
            </el-button>
            <el-button
              type="success"
              size="small"
              @click="handleOpenMemberSetting(scope.row)"
            >
              设置
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
        <el-descriptions-item label="会员类型">
          <el-tag :type="getMemberTypeTag(currentUser.member_type)" size="small">
            {{ getMemberTypeText(currentUser.member_type) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="会员开通时间">{{ formatDateTime(currentUser.member_start_at) }}</el-descriptions-item>
        <el-descriptions-item label="会员到期时间">{{ formatDateTime(currentUser.member_end_at) }}</el-descriptions-item>
        <el-descriptions-item label="剩余时间">{{ getRemainingText(currentUser) }}</el-descriptions-item>
        <el-descriptions-item label="已用识别次数">{{ currentUser.recognition_used != null ? currentUser.recognition_used : 0 }}</el-descriptions-item>
      </el-descriptions>
      <span slot="footer" class="dialog-footer">
        <el-button @click="detailDialogVisible = false">关 闭</el-button>
      </span>
    </el-dialog>

    <!-- 会员设置对话框 -->
    <el-dialog
      title="设置会员等级"
      :visible.sync="memberSettingVisible"
      width="420px"
      @close="memberSettingForm = getDefaultMemberForm()"
    >
      <el-form ref="memberForm" :model="memberSettingForm" label-width="100px" size="small">
        <el-form-item label="用户">
          <span>{{ memberSettingForm.username || '-' }}</span>
        </el-form-item>
        <el-form-item label="会员类型" prop="member_type">
          <el-select v-model="memberSettingForm.member_type" placeholder="请选择" style="width: 100%">
            <el-option label="普通用户" value="normal" />
            <el-option label="免费用户（3个月）" value="free" />
            <el-option label="月付会员" value="monthly" />
            <el-option label="年付会员" value="yearly" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="memberSettingForm.member_type === 'free'" label="说明">
          <span class="tip">免费用户使用期限为 3 个月，到期后需升级为付费会员</span>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="memberSettingVisible = false">取 消</el-button>
        <el-button type="primary" :loading="memberSettingSaving" @click="handleSaveMemberSetting">保 存</el-button>
      </span>
    </el-dialog>

    <!-- 批量设置会员对话框 -->
    <el-dialog
      title="批量设置会员类型"
      :visible.sync="batchMemberVisible"
      width="420px"
      @close="batchMemberForm = getDefaultBatchMemberForm()"
    >
      <el-form :model="batchMemberForm" label-width="100px" size="small">
        <el-form-item label="已选择">
          <span>{{ selectedUsers.length }} 个用户</span>
        </el-form-item>
        <el-form-item label="会员类型" prop="member_type">
          <el-select v-model="batchMemberForm.member_type" placeholder="请选择" style="width: 100%">
            <el-option label="普通用户" value="normal" />
            <el-option label="免费用户（3个月）" value="free" />
            <el-option label="月付会员" value="monthly" />
            <el-option label="年付会员" value="yearly" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="batchMemberForm.member_type === 'free'" label="说明">
          <span class="tip">免费用户使用期限为 3 个月（后端会自动设置到期时间）</span>
        </el-form-item>
      </el-form>
      <span slot="footer" class="dialog-footer">
        <el-button @click="batchMemberVisible = false">取 消</el-button>
        <el-button type="primary" :loading="batchMemberSaving" @click="saveBatchMemberType">保 存</el-button>
      </span>
    </el-dialog>
  </div>
</template>

<script>
import { getUsersList, getUserDetail, deleteUser, updateUser } from '@/api/user'

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
      currentUser: null,
      memberSettingVisible: false,
      memberSettingSaving: false,
      memberSettingForm: {
        id: '',
        username: '',
        member_type: 'normal'
      },
      selectedUsers: [],
      batchMemberVisible: false,
      batchMemberSaving: false,
      batchMemberForm: {
        member_type: 'normal'
      },
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

    handleSelectionChange(rows) {
      this.selectedUsers = Array.isArray(rows) ? rows : []
    },

    getDefaultMemberForm() {
      return { id: '', username: '', member_type: 'normal' }
    },

    getDefaultBatchMemberForm() {
      return { member_type: 'normal' }
    },

    handleOpenMemberSetting(row) {
      this.memberSettingForm = {
        id: row.id,
        username: row.username,
        member_type: row.member_type || 'normal'
      }
      this.memberSettingVisible = true
    },

    async handleSaveMemberSetting() {
      this.memberSettingSaving = true
      try {
        const res = await updateUser(this.memberSettingForm.id, {
          member_type: this.memberSettingForm.member_type
        })
        if (res.success) {
          this.$message.success('保存成功')
          this.memberSettingVisible = false
          this.fetchUsers()
        } else {
          this.$message.error(res.message || '保存失败')
        }
      } catch (error) {
        console.error('保存失败:', error)
        this.$message.error('保存失败')
      } finally {
        this.memberSettingSaving = false
      }
    },

    openBatchMemberDialog() {
      if (!this.selectedUsers.length) return
      this.batchMemberForm = { member_type: 'normal' }
      this.batchMemberVisible = true
    },

    async saveBatchMemberType() {
      if (!this.selectedUsers.length) {
        this.$message.warning('请先选择用户')
        return
      }
      this.batchMemberSaving = true
      const ids = this.selectedUsers.map((u) => u.id).filter(Boolean)
      let ok = 0
      let fail = 0
      try {
        await Promise.all(
          ids.map(async (id) => {
            try {
              const res = await updateUser(id, { member_type: this.batchMemberForm.member_type })
              if (res && res.success) ok += 1
              else fail += 1
            } catch (e) {
              fail += 1
            }
          }),
        )
        if (ok) this.$message.success(`批量设置成功：${ok} 个`)
        if (fail) this.$message.error(`批量设置失败：${fail} 个`)
        this.batchMemberVisible = false
        this.fetchUsers()
      } finally {
        this.batchMemberSaving = false
      }
    },

    getRemainingText(row) {
      if (!row) return '-'
      const type = row.member_type || 'normal'
      if (type !== 'free') return type === 'normal' ? '-' : '不限'
      const end = row.member_end_at
      if (!end) return '-'
      try {
        const endStr = String(end).replace('T', ' ').slice(0, 19)
        const endDate = new Date(endStr.replace(/-/g, '/'))
        const now = new Date()
        if (endDate <= now) return '已到期'
        const days = Math.ceil((endDate - now) / (24 * 60 * 60 * 1000))
        return days + ' 天'
      } catch (e) {
        return '-'
      }
    },

    formatDateTime(val) {
      if (!val) return '-'
      const s = String(val).replace('T', ' ')
      return s.length >= 19 ? s.slice(0, 19) : s
    },

    getMemberTypeText(type) {
      const map = { normal: '普通用户', free: '免费用户', monthly: '月付会员', yearly: '年付会员' }
      return map[type] || type || '普通用户'
    },

    getMemberTypeTag(type) {
      const map = { normal: 'info', free: 'primary', monthly: 'success', yearly: 'warning' }
      return map[type] || 'info'
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

  .tip {
    font-size: 12px;
    color: #909399;
  }
}
</style>
