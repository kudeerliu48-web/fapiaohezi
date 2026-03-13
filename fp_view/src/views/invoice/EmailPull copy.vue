<template>
  <div class="email-panel">
    <el-form :inline="true" :model="form" size="small">
      <el-form-item label="邮箱地址">
        <el-input v-model="form.mailbox" placeholder="未设置邮箱" style="width: 260px" :disabled="true" />
      </el-form-item>
      <el-form-item label="授权码">
        <el-input v-model="form.authCode" placeholder="请输入授权码" type="password" show-password style="width: 240px" />
      </el-form-item>
      <el-form-item label="时间范围">
        <el-select v-model="form.rangeKey" placeholder="请选择">
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
          class="ui-btn ui-btn--primary"
          :loading="submitting || isRunning"
          :disabled="submitting || isRunning"
          @click="start"
        >开始拉取</el-button>
      </el-form-item>
    </el-form>

    <div v-if="task && task.status !== 'not_found'" class="email-stats">
      <el-row :gutter="12">
        <el-col :span="4">
          <div class="stat-card">
            <div class="stat-label">已扫描邮件</div>
            <div class="stat-value">{{ stats.scanned_emails }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-card">
            <div class="stat-label">匹配邮件数</div>
            <div class="stat-value">{{ stats.matched_emails }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-card">
            <div class="stat-label">已下载附件</div>
            <div class="stat-value">{{ stats.downloaded_attachments }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-card">
            <div class="stat-label">已导入发票</div>
            <div class="stat-value">{{ stats.imported_invoices }}</div>
          </div>
        </el-col>
        <el-col :span="4">
          <div class="stat-card">
            <div class="stat-label">失败数量</div>
            <div class="stat-value error">{{ stats.failed_count }}</div>
          </div>
        </el-col>
      </el-row>
    </div>

    <div v-if="task && task.status !== 'not_found'" class="email-status">
      当前状态：{{ statusLabel(task.status) }}
    </div>

    <div v-if="canRecognize" class="email-actions">
      <el-button
        type="primary"
        class="ui-btn ui-btn--primary"
        :loading="recognizing"
        :disabled="recognizing"
        @click="recognizeBatch"
      >一键识别</el-button>
    </div>
  </div>
</template>

<script>
import workbenchAPI from '@/api/workbench'
import api from '@/api/auth'
import { authAPI } from '@/api/auth'

export default {
  name: 'EmailPull',
  props: {
    userId: { type: String, required: true },
  },
  data() {
    return {
      submitting: false,
      form: { mailbox: '', authCode: '', rangeKey: '3m' },
      task: null,
      stats: { scanned_emails: 0, matched_emails: 0, downloaded_attachments: 0, imported_invoices: 0, failed_count: 0 },
      timer: null,
      recognizing: false,
      streamSource: null,
    }
  },
  computed: {
    isRunning() {
      const s = this.task?.status
      return s === 'queued' || s === 'running'
    },
    canRecognize() {
      const s = this.task?.status
      return !!(this.task?.batch_id && (s === 'completed' || s === 'partial_success') && (this.stats.imported_invoices || 0) > 0)
    },
  },
  async mounted() {
    // 默认展示用户邮箱（不要求手动填写）
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

    // 进入页面时拉取最近一次任务，用于展示统计卡片
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
      this.streamSource = null
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
      const { authCode, rangeKey } = this.form
      if (!authCode) {
        this.$message.warning('请填写授权码')
        return
      }
      this.submitting = true
      try {
        // 邮箱地址由后端根据用户信息自动解析；前端不强制传 mailbox
        const task = await workbenchAPI.startEmailPushTask(this.userId, { authCode, rangeKey })
        this.task = task
        this.updateStats()
        this.$message.success('邮箱拉取任务已启动')
        this.startPolling()
      } catch (e) {
        this.$message.error(`启动邮箱拉取失败：${e.message}`)
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
          if (['completed', 'failed', 'partial_success', 'cancelled'].includes(this.task.status)) {
            clearInterval(this.timer)
            this.timer = null
            this.$emit('refresh')
          }
        } catch (e) {}
      }, 3000)
    },

    async recognizeBatch() {
      if (!this.task?.batch_id) return
      this.recognizing = true
      try {
        const res = await api.post(`/invoices/submit/${this.userId}/${this.task.batch_id}`, {}, { timeout: 300000 })
        if (!res.data?.success) {
          throw new Error(res.data?.message || '提交识别失败')
        }
        this.$message.success('识别任务已提交，正在处理中...')
        this.pollBatchStream(this.task.batch_id)
      } catch (e) {
        this.$message.error(`提交识别失败：${e.message}`)
      } finally {
        this.recognizing = false
      }
    },

    pollBatchStream(batchId) {
      if (!batchId) return
      if (this.streamSource) {
        try { this.streamSource.close() } catch (e) {}
        this.streamSource = null
      }
      const url = `http://localhost:8000/api/invoices/batches/${batchId}/stream?user_id=${encodeURIComponent(this.userId)}`
      const es = new EventSource(url)
      this.streamSource = es

      es.addEventListener('batch_done', () => {
        try { es.close() } catch (e) {}
        this.streamSource = null
        this.$emit('refresh')
      })

      es.onerror = () => {
        try { es.close() } catch (e) {}
        this.streamSource = null
      }
    },
  },
}
</script>

<style scoped lang="scss">
.email-panel {
  padding: 10px;
}

.email-stats {
  margin-top: 20px;
}

.stat-card {
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
}
.stat-label {
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
}
.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}
.stat-value.error {
  color: #b91c1c;
}

.email-status {
  margin-top: 16px;
  padding: 12px;
  background: #f0f9ff;
  border-radius: 8px;
  font-size: 14px;
  color: #0369a1;
}

.email-actions {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
</style>

