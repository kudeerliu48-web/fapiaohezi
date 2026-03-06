export const INVOICE_STATUS = {
  0: { label: '处理中', type: 'info', color: '#909399' },
  1: { label: '识别成功', type: 'success', color: '#67C23A' },
  2: { label: '识别失败', type: 'danger', color: '#F56C6C' },
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

