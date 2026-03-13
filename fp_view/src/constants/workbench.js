export const INVOICE_STATUS = {
  0: { label: '待处理', type: 'info', color: '#909399' },
  1: { label: '已完成', type: 'success', color: '#67C23A' },
  2: { label: '失败', type: 'danger', color: '#F56C6C' },
}

export const INVOICE_RUNTIME_STATUS = {
  pending: { label: '待处理', type: 'info', color: '#909399' },
  queued: { label: '排队中', type: 'warning', color: '#E6A23C' },
  running: { label: '处理中', type: 'warning', color: '#E6A23C' },
  completed: { label: '已完成', type: 'success', color: '#67C23A' },
  failed: { label: '失败', type: 'danger', color: '#F56C6C' },
}

export const BATCH_STATUS = {
  empty: { label: '空批次', type: 'info' },
  processing: { label: '处理中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' },
  partial_completed: { label: '部分完成', type: 'warning' },
}

export const STEP_META = {
  preprocess: { label: '预处理', order: 1 },
  ocr: { label: 'OCR识别', order: 2 },
  normalize: { label: '清洗标准化', order: 3 },
  validate: { label: '校验修复', order: 4 },
  finalize: { label: '最终入库', order: 5 },
}

export const STEP_STATUS = {
  pending: { label: '待执行', type: 'info' },
  running: { label: '执行中', type: 'warning' },
  success: { label: '成功', type: 'success' },
  failed: { label: '失败', type: 'danger' },
  skipped: { label: '已跳过', type: 'info' },
}

export const TASK_STATUS = {
  queued: { label: '排队中', type: 'info' },
  running: { label: '处理中', type: 'warning' },
  completed: { label: '已完成', type: 'success' },
  failed: { label: '失败', type: 'danger' },
  partial_success: { label: '部分成功', type: 'warning' },
  cancelled: { label: '已取消', type: 'info' },
  not_found: { label: '任务不存在', type: 'info' },
}

export const TASK_TYPE = {
  recognize_batch: '批次识别',
  email_pull: '邮箱拉取',
}

export const EMAIL_STAGE = {
  queued: '排队中',
  connect_imap: '连接邮箱',
  select_mailbox: '选择邮箱文件夹',
  search_emails: '搜索邮件',
  filter_emails: '过滤邮件',
  parse_message: '解析邮件',
  download_attachment: '下载附件',
  import_invoice: '导入发票',
  trigger_recognition: '触发识别',
  finalize: '汇总结果',
}
