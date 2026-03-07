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

    <div v-if="task.current_invoice_name" class="panel-line">
      当前处理：{{ task.current_invoice_name }}
    </div>
    <div v-if="latestLog" class="panel-line latest-log">
      最新日志：{{ latestLog }}
    </div>
  </el-card>
</template>

<script>
import { TASK_STATUS, TASK_TYPE } from '@/constants/workbench'

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
</style>
