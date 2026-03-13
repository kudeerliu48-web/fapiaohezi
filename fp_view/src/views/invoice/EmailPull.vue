<template>
  <div class="email-panel">
    <div class="config-section">
      <el-form :inline="true" :model="form" size="medium" class="modern-form">
        <el-form-item label="邮箱地址">
          <el-input 
            v-model="form.mailbox" 
            placeholder="未设置邮箱" 
            class="styled-input readonly-input"
            style="width: 240px" 
            disabled 
          >
            <i slot="prefix" class="el-icon-message"></i>
          </el-input>
        </el-form-item>
        <el-form-item label="授权码">
          <el-input 
            v-model="form.authCode" 
            placeholder="请输入授权码" 
            type="password" 
            show-password 
            class="styled-input"
            style="width: 220px" 
          >
            <i slot="prefix" class="el-icon-key"></i>
          </el-input>
        </el-form-item>
        <el-form-item label="范围">
          <el-select v-model="form.rangeKey" style="width: 140px" class="styled-select">
            <el-option label="最近 7 天" value="7d" />
            <el-option label="最近 1 个月" value="1m" />
            <el-option label="最近 3 个月" value="3m" />
            <el-option label="最近 6 个月" value="6m" />
            <el-option label="最近 12 个月" value="12m" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            class="action-btn-main"
            :loading="submitting || isRunning"
            :disabled="submitting || isRunning"
            @click="start"
          >
            {{ isRunning ? '正在拉取...' : '开始拉取' }}
          </el-button>
        </el-form-item>
      </el-form>
      <div class="authcode-tip">
        提示：授权码需要在邮箱服务提供商后台单独开通，例如：
        163/QQ 邮箱请在「账号安全」或「客户端授权码」页面生成专用授权码，
        再复制粘贴到上面的输入框中（不是登录密码）。
      </div>
    </div>

    <transition name="el-zoom-in-top">
      <div v-if="task && task.status !== 'not_found'" class="stats-container">
        <el-row :gutter="20">
          <el-col :span="4" v-for="(item, index) in statsConfig" :key="index">
            <div class="stat-glass-card" :class="item.type">
              <div class="icon-box">
                <i :class="item.icon"></i>
              </div>
              <div class="text-content">
                <div class="label">{{ item.label }}</div>
                <div class="value">{{ item.value }}</div>
              </div>
            </div>
          </el-col>
        </el-row>
      </div>
    </transition>

    <div v-if="task && task.status !== 'not_found'" class="status-indicator-bar" :class="task.status">
      <div class="status-left">
        <span class="pulse-dot" v-if="isRunning"></span>
        <i :class="statusIcon(task.status)" class="status-main-icon"></i>
        <span class="status-text">任务状态：<strong>{{ statusLabel(task.status) }}</strong></span>
      </div>
      <div class="status-right" v-if="isRunning">
        <el-button type="text" icon="el-icon-loading">实时同步中</el-button>
      </div>
    </div>

    <div v-if="hasBatchToRecognize" class="bottom-actions">
      <div class="tips">
        <i class="el-icon-info"></i> 已导入 {{ stats.imported_invoices }} 张发票，可以开始智能识别
        <span v-if="!quotaCanRecognize" class="quota-tip">（{{ quotaMessage }}）</span>
      </div>
      <el-button
        type="success"
        icon="el-icon-cpu"
        class="recognize-btn"
        :loading="recognizing"
        :disabled="!quotaCanRecognize"
        @click="recognizeBatch"
      >一键识别</el-button>
    </div>
  </div>
</template>

<script>
import workbenchAPI from '@/api/workbench'
import api from '@/api/auth'
import { authAPI } from '@/api/auth'
import config from '@/config'

export default {
  name: 'EmailPull',
  props: {
    userId: { type: String, required: true },
    canRecognize: { type: Boolean, default: true },
    quotaMessage: { type: String, default: '' },
  },
  data() {
    return {
      submitting: false,
      recognizing: false,
      // 核心修复：确保 form 正确初始化
      form: { 
        mailbox: '', 
        authCode: '', 
        rangeKey: '3m' 
      },
      task: null,
      stats: { 
        scanned_emails: 0, 
        matched_emails: 0, 
        downloaded_attachments: 0, 
        imported_invoices: 0, 
        failed_count: 0 
      },
      timer: null,
      streamSource: null,
    }
  },
  computed: {
    isRunning() {
      const s = this.task?.status
      return s === 'queued' || s === 'running'
    },
    hasBatchToRecognize() {
      const s = this.task?.status
      return !!(this.task?.batch_id && (s === 'completed' || s === 'partial_success') && (this.stats.imported_invoices || 0) > 0)
    },
    quotaCanRecognize() {
      return this.canRecognize !== false
    },
    statsConfig() {
      return [
        { label: '已扫描邮件', value: this.stats.scanned_emails, icon: 'el-icon-monitor', type: 'info' },
        { label: '匹配邮件数', value: this.stats.matched_emails, icon: 'el-icon-aim', type: 'primary' },
        { label: '已下载附件', value: this.stats.downloaded_attachments, icon: 'el-icon-download', type: 'success' },
        { label: '已导入发票', value: this.stats.imported_invoices, icon: 'el-icon-document-checked', type: 'warning' },
        { label: '失败数量', value: this.stats.failed_count, icon: 'el-icon-warning-outline', type: 'danger' },
      ]
    }
  },
  async mounted() {
    // 获取用户邮箱
    try {
      const cached = JSON.parse(localStorage.getItem('user') || '{}')
      if (cached?.email) {
        this.form.mailbox = cached.email
      } else if (this.userId) {
        const res = await authAPI.getUserInfo(this.userId)
        const email = res?.data?.data?.email || res?.data?.email
        if (email) this.form.mailbox = email
      }
    } catch (e) {}

    // 拉取最近任务状态
    try {
      const latest = await workbenchAPI.getLatestEmailPushTask(this.userId)
      if (latest && latest.status && latest.status !== 'not_found') {
        this.task = latest
        this.updateStats()
        if (this.isRunning) this.startPolling()
      }
    } catch (e) {}
  },
  beforeDestroy() {
    if (this.timer) clearInterval(this.timer)
    if (this.streamSource) {
      try { this.streamSource.close() } catch (e) {}
    }
  },
  methods: {
    statusLabel(status) {
      const map = {
        queued: '排队中',
        running: '处理中',
        completed: '已完成',
        failed: '失败',
        partial_success: '部分成功',
        cancelled: '已取消',
      }
      return map[status] || status || '-'
    },
    statusIcon(status) {
      const map = {
        queued: 'el-icon-timer',
        running: 'el-icon-loading',
        completed: 'el-icon-success',
        failed: 'el-icon-error',
        partial_success: 'el-icon-warning'
      }
      return map[status] || 'el-icon-info'
    },
    updateStats() {
      const t = this.task || {}
      this.stats = {
        scanned_emails: t.scanned_emails || 0,
        matched_emails: t.matched_emails || 0,
        downloaded_attachments: t.downloaded_attachments || 0,
        imported_invoices: t.imported_invoices || 0,
        failed_count: t.failed_count || 0,
      }
    },
    async start() {
      if (!this.form.authCode) {
        this.$message.warning('请填写授权码')
        return
      }
      this.submitting = true
      try {
        const task = await workbenchAPI.startEmailPushTask(this.userId, { 
          authCode: this.form.authCode, 
          rangeKey: this.form.rangeKey 
        })
        this.task = task
        this.updateStats()
        this.$message.success('邮箱拉取任务已启动')
        this.startPolling()
      } catch (e) {
        this.$message.error(`启动失败：${e.message}`)
      } finally {
        this.submitting = false
      }
    },
    startPolling() {
      if (this.timer) clearInterval(this.timer)
      this.timer = setInterval(async () => {
        try {
          if (!this.task?.job_id) return
          const task = await workbenchAPI.getEmailPushTaskStatus(this.task.job_id, this.userId)
          this.task = task
          this.updateStats()
          if (!this.isRunning) {
            clearInterval(this.timer)
            this.$emit('refresh')
          }
        } catch (e) {}
      }, 3000)
    },
    async recognizeBatch() {
      if (!this.task?.batch_id) return
      if (!this.quotaCanRecognize && this.quotaMessage) {
        this.$message.warning(this.quotaMessage)
        return
      }
      this.recognizing = true
      try {
        const res = await api.post(`/invoices/submit/${this.userId}/${this.task.batch_id}`)
        if (!res.data?.success) {
          const msg = res.data?.message || '提交识别失败'
          if (res.data?.code === 403 || msg.includes('识别次数已用完') || msg.includes('会员已到期')) {
            this.showQuotaExhaustedDialog()
            return
          }
          throw new Error(msg)
        }
        this.$message.success('识别任务已提交，正在获取结果...')
        this.pollBatchStream(this.task.batch_id)
      } catch (e) {
        const code = e.response?.data?.code
        const msg = e.response?.data?.message || e.message
        const isQuotaError = e.response?.status === 403 || code === 403 || (msg && (msg.includes('识别次数已用完') || msg.includes('会员已到期')))
        if (isQuotaError) {
          this.showQuotaExhaustedDialog()
        } else {
          this.$message.error(`提交识别失败：${msg}`)
        }
      } finally {
        this.recognizing = false
      }
    },
    showQuotaExhaustedDialog() {
      this.$alert('您的识别额度已用完，请前往充值或升级会员后继续使用。', '额度已用完', {
        confirmButtonText: '前往充值',
        type: 'warning',
        callback: () => {
          if (this.$router) this.$router.push('/recharge')
        }
      })
    },

    pollBatchStream(batchId) {
      if (!batchId) return
      // 关闭之前的流
      if (this.streamSource) {
        try { this.streamSource.close() } catch (e) {}
        this.streamSource = null
      }

      const url = `${config.API_PREFIX}/invoices/batches/${batchId}/stream?user_id=${encodeURIComponent(this.userId)}`
      const es = new EventSource(url)
      this.streamSource = es

      // 这里只要确保真正调用了查询结果接口，最终批次完成就刷新一次列表即可
      es.addEventListener('batch_done', () => {
        try { es.close() } catch (e) {}
        this.streamSource = null
        this.$emit('refresh')
      })

      es.onerror = () => {
        try { es.close() } catch (e) {}
        this.streamSource = null
      }
    }
  }
}
</script>

<style scoped lang="scss">
.email-panel { padding: 15px; background-color: #ffffff; }

/* 配置区域 */
.config-section {
  background: #f8fafc;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  margin-bottom: 24px;
}
.modern-form {
  display: flex; align-items: center; flex-wrap: wrap; gap: 10px;
  ::v-deep .el-form-item { margin-bottom: 0; margin-right: 20px;
    .el-form-item__label { font-weight: 600; color: #475569; }
  }
}
.styled-input {
  ::v-deep .el-input__inner { border-radius: 8px; border: 1px solid #cbd5e1; transition: all 0.3s;
    &:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1); }
  }
}
.readonly-input { ::v-deep .el-input__inner { background-color: #f1f5f9; color: #64748b; } }

.authcode-tip {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.6;
}

.action-btn-main {
  padding: 10px 25px; border-radius: 8px; font-weight: 600; transition: all 0.3s;
  &:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); }
}

/* 卡片样式 */
.stats-container { margin-bottom: 24px; }
.stat-glass-card {
  display: flex; align-items: center; padding: 16px; background: #fff; border-radius: 12px;
  border: 1px solid #f1f5f9; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); transition: all 0.3s;
  &:hover { transform: translateY(-3px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
  .icon-box { width: 44px; height: 44px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 20px; margin-right: 12px; }
  .text-content { .label { font-size: 13px; color: #64748b; margin-bottom: 4px; } .value { font-size: 20px; font-weight: 700; color: #1e293b; } }
  
  &.info .icon-box { background: #eff6ff; color: #3b82f6; }
  &.primary .icon-box { background: #f0fdf4; color: #22c55e; }
  &.success .icon-box { background: #f0f9ff; color: #0ea5e9; }
  &.warning .icon-box { background: #fffbeb; color: #f59e0b; }
  &.danger .icon-box { background: #fef2f2; color: #ef4444; }
}

/* 状态反馈条 */
.status-indicator-bar {
  display: flex; justify-content: space-between; align-items: center; padding: 14px 20px;
  border-radius: 10px; font-size: 14px; border-left: 4px solid #3b82f6;
  &.running { background: #f0f9ff; border-color: #3b82f6; color: #1d4ed8; }
  &.completed { background: #f0fdf4; border-color: #22c55e; color: #15803d; }
  &.failed { background: #fef2f2; border-color: #ef4444; color: #b91c1c; }
  .status-left { display: flex; align-items: center; gap: 10px; }
  .status-main-icon { font-size: 18px; }
  .pulse-dot { width: 8px; height: 8px; background: #3b82f6; border-radius: 50%; animation: pulse 1.5s infinite; }
}

.bottom-actions {
  margin-top: 30px; display: flex; justify-content: space-between; align-items: center;
  padding: 20px; background: #fafafa; border-radius: 12px; border: 1px dashed #cbd5e1;
  .tips { color: #64748b; font-size: 14px; i { color: #22c55e; margin-right: 5px; } }
  .quota-tip { color: #f59e0b; margin-left: 6px; font-size: 13px; }
  .recognize-btn { padding: 12px 30px; font-size: 15px; font-weight: 600; border-radius: 8px; }
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(59, 130, 246, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(59, 130, 246, 0); }
}
</style>