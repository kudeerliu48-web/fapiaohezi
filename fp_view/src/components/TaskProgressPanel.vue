<template>
  <el-card v-if="task" class="task-progress-panel" shadow="never">
    <div class="panel-head">
      <div class="head-left">
        <div class="panel-title">{{ title || taskTypeLabel }}</div>
        <div class="head-tags">
          <el-tag size="mini" type="info">{{ taskTypeLabel }}</el-tag>
          <el-tag size="mini" :type="statusMeta.type">{{ statusMeta.label }}</el-tag>
        </div>
      </div>
      <el-button type="text" icon="el-icon-close" @click="$emit('close')">收起</el-button>
    </div>

    <div class="panel-stats">
      <span>总数 {{ total }}</span>
      <span>完成 {{ completed }}</span>
      <span>失败 {{ failed }}</span>
      <span>进度 {{ percent }}%</span>
    </div>

    <el-progress :percentage="percent" :status="progressStatus" :stroke-width="10" />

    <div v-if="isEmailTask" class="panel-stats email-stats">
      <span>扫描 {{ scanned }}</span>
      <span>匹配 {{ matched }}</span>
      <span>下载 {{ downloaded }}</span>
      <span>导入 {{ imported }}</span>
      <span>识别 {{ recognized }}</span>
    </div>

    <div v-if="isEmailTask && stageLabel" class="panel-line">
      当前阶段：{{ stageLabel }}
    </div>
    <div v-if="isEmailTask && task.current_email_subject" class="panel-line">
      当前邮件：{{ task.current_email_subject }}
    </div>
    <div v-if="isEmailTask && task.current_attachment_name" class="panel-line">
      当前附件：{{ task.current_attachment_name }}
    </div>
    <div v-if="task.current_invoice_name" class="panel-line">
      当前处理：{{ task.current_invoice_name }}
    </div>
    <div v-if="latestLog" class="panel-line latest-log">
      最新日志：{{ latestLog }}
    </div>

    <div v-if="visibleLogs.length" class="panel-logs">
      <div class="logs-title">最近日志</div>
      <div
        v-for="(log, index) in visibleLogs"
        :key="index"
        class="log-item"
        :class="{ error: isErrorLog(log) }"
      >
        {{ log }}
      </div>
    </div>
  </el-card>
</template>

<script>
import { TASK_STATUS, TASK_TYPE, EMAIL_STAGE } from '@/constants/workbench'

export default {
  name: 'TaskProgressPanel',
  props: {
    task: {
      type: Object,
      default: null,
    },
    title: {
      type: String,
      default: '',
    },
  },
  computed: {
    statusMeta() {
      return TASK_STATUS[this.task?.status] || { label: this.task?.status || '-', type: 'info' }
    },
    taskTypeLabel() {
      return TASK_TYPE[this.task?.task_type] || '后台任务'
    },
    total() {
      return Number(this.task?.total || 0)
    },
    completed() {
      return Number(this.task?.completed || 0)
    },
    failed() {
      return Number(this.task?.failed || 0)
    },
    percent() {
      const p = Number(this.task?.progress_percent || 0)
      if (Number.isNaN(p)) return 0
      return Math.max(0, Math.min(100, Math.round(p)))
    },
    progressStatus() {
      if (this.task?.status === 'failed') return 'exception'
      if (this.task?.status === 'completed') return 'success'
      return null
    },
    latestLog() {
      const logs = this.task?.logs || []
      if (!Array.isArray(logs) || !logs.length) return ''
      return logs[logs.length - 1]
    },
    isEmailTask() {
      return this.task?.task_type === 'email_pull'
    },
    stageLabel() {
      if (!this.isEmailTask) return ''
      const stage = this.task?.current_stage || ''
      return EMAIL_STAGE[stage] || stage
    },
    visibleLogs() {
      const logs = this.task?.logs || []
      if (!Array.isArray(logs)) return []
      return logs.slice(-12).reverse()
    },
    scanned() {
      return Number(this.task?.scanned_emails || this.task?.total_messages || 0)
    },
    matched() {
      return Number(this.task?.matched_emails || this.task?.matched_messages || 0)
    },
    downloaded() {
      return Number(this.task?.downloaded_attachments || this.task?.downloaded || 0)
    },
    imported() {
      return Number(this.task?.imported_invoices || this.task?.imported || 0)
    },
    recognized() {
      return Number(this.task?.recognized_invoices || 0)
    },
  },
  methods: {
    isErrorLog(log) {
      const text = String(log || '')
      return text.includes('错误') || text.includes('失败')
    },
  },
}
</script>

<style scoped lang="scss">
.task-progress-panel {
  border-radius: 10px;
  margin-bottom: 12px;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.head-tags {
  margin-top: 4px;
  display: flex;
  gap: 6px;
}

.panel-stats {
  display: flex;
  gap: 14px;
  color: #606266;
  font-size: 12px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.email-stats {
  margin-top: 8px;
}

.panel-line {
  margin-top: 8px;
  font-size: 12px;
  color: #606266;
  word-break: break-all;
}

.latest-log {
  color: #909399;
}

.panel-logs {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid #ebeef5;
  max-height: 220px;
  overflow-y: auto;
}

.logs-title {
  font-size: 12px;
  color: #606266;
  margin-bottom: 6px;
}

.log-item {
  font-size: 12px;
  line-height: 1.6;
  color: #606266;
}

.log-item.error {
  color: #f56c6c;
}
</style>
