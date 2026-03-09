import api from './auth'

function unwrap(res) {
  const payload = res?.data
  if (!payload?.success) {
    throw new Error(payload?.message || '请求失败')
  }
  return payload.data
}

export const workbenchAPI = {
  async uploadBatch(userId, files, remark = '') {
    const formData = new FormData()
    files.forEach((f) => formData.append('files', f.raw || f))
    if (remark) {
      formData.append('remark', remark)
    }
    const res = await api.post(`/workbench/batches/${userId}/upload`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
    return unwrap(res)
  },

  async getOverview(userId) {
    return unwrap(await api.get(`/workbench/overview/${userId}`))
  },

  async getBatches(userId, params = {}) {
    return unwrap(await api.get(`/workbench/batches/${userId}`, { params }))
  },

  async getInvoices(userId, params = {}) {
    return unwrap(await api.get(`/workbench/invoices/${userId}`, { params }))
  },

  async getBatchInvoices(userId, batchId, params = {}) {
    return unwrap(await api.get(`/workbench/batch/${userId}/${batchId}/invoices`, { params }))
  },

  async getInvoiceDetail(userId, invoiceId) {
    return unwrap(await api.get(`/workbench/invoice/${userId}/${invoiceId}`))
  },

  async getInvoiceSteps(userId, invoiceId) {
    return unwrap(await api.get(`/workbench/invoice/${userId}/${invoiceId}/steps`))
  },

  async retryInvoice(userId, invoiceId) {
    return unwrap(await api.post(`/workbench/invoice/${userId}/${invoiceId}/retry`, {}, {
      timeout: 300000,
    }))
  },

  async retryBatch(userId, batchId) {
    return unwrap(await api.post(`/workbench/batch/${userId}/${batchId}/retry`))
  },

  async deleteInvoice(userId, invoiceId) {
    return unwrap(await api.delete(`/workbench/invoice/${userId}/${invoiceId}`))
  },

  async deleteBatch(userId, batchId) {
    return unwrap(await api.delete(`/workbench/batch/${userId}/${batchId}`))
  },

  async clearAllHistory(userId) {
    return unwrap(await api.delete(`/workbench/history/${userId}/all`))
  },

  // OCR 识别所有未识别发票
  async recognizeUnrecognized(userId, batchId = '') {
    return unwrap(await api.post(`/workbench/recognize-unrecognized`, {
      user_id: userId,
      batch_id: batchId || undefined,
    }))
  },

  // 查询最近识别任务
  async getLatestRecognizeTask(userId, batchId = '') {
    return unwrap(await api.get(`/workbench/recognize-latest/${userId}`, {
      params: { batch_id: batchId || undefined },
    }))
  },

  // 启动邮箱拉取任务
  async startEmailPushTask(userId, payload) {
    const formData = new FormData()
    formData.append('range_key', payload.rangeKey || '3m')
    if (payload.mailbox) formData.append('mailbox', payload.mailbox)
    formData.append('auth_code', payload.authCode)
    if (payload.startDate) formData.append('start_date', payload.startDate)
    if (payload.endDate) formData.append('end_date', payload.endDate)

    return unwrap(await api.post(`/workbench/email-push/${userId}/start`, formData, {
      timeout: 60000,
      headers: { 'Content-Type': 'multipart/form-data' },
    }))
  },

  // 查询最近邮箱拉取任务
  async getLatestEmailPushTask(userId) {
    return unwrap(await api.get(`/workbench/email-push/latest/${userId}`))
  },

  // 查询邮箱拉取任务状态
  async getEmailPushTaskStatus(jobId, userId = '') {
    return unwrap(await api.get(`/workbench/email-push/status/${jobId}`, {
      params: { user_id: userId || undefined },
    }))
  },
}

export default workbenchAPI
