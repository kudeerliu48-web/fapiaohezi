import api from './auth'

function unwrap(res) {
  const payload = res?.data
  if (!payload?.success) {
    throw new Error(payload?.message || '请求失败')
  }
  return payload.data
}

export const workbenchAPI = {
  async submitInvoices(files, userId) {
    // fp_api_new：上传发票文件并创建批次
    const formData = new FormData()
    const normalizedFiles = Array.isArray(files) ? files : [files]
    normalizedFiles.forEach((f) => formData.append('files', f.raw || f))
    const res = await api.post(`/invoices/upload/${userId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
    return unwrap(res)
  },

  async uploadBatch(userId, files) {
    const formData = new FormData()
    files.forEach((f) => formData.append('files', f.raw || f))
    const res = await api.post(`/invoices/upload/${userId}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
    return unwrap(res)
  },

  async getInvoices(userId, params = {}) {
    return unwrap(await api.get(`/invoices/${userId}`, { params }))
  },

  /** 基于原发票新增一条记录（表单编辑后提交，新记录状态=99，排在原行下） */
  async deriveInvoice(userId, invoiceId, body) {
    return unwrap(await api.post(`/invoices/${userId}/${invoiceId}/derive`, body))
  },

  /** 更新新增行（仅 recognition_status=99 可编辑） */
  async updateInvoice(userId, invoiceId, body) {
    return unwrap(await api.put(`/invoices/${userId}/${invoiceId}`, body))
  },

  /** 仅更新备注（原始行/新增行均可） */
  async updateInvoiceRemark(userId, invoiceId, remark) {
    return unwrap(await api.patch(`/invoices/${userId}/${invoiceId}/remark`, { remark: remark ?? '' }))
  },

  async getBatchStream(batchId, params = {}) {
    return unwrap(await api.get(`/invoices/batches/${batchId}/stream`, { params }))
  },

  // 启动邮箱拉取任务
  async startEmailPushTask(userId, payload) {
    const formData = new FormData()
    formData.append('range_key', payload.rangeKey || '3m')
    if (payload.mailbox) formData.append('mailbox', payload.mailbox)
    formData.append('auth_code', payload.authCode)
    if (payload.startDate) formData.append('start_date', payload.startDate)
    if (payload.endDate) formData.append('end_date', payload.endDate)

    return unwrap(await api.post(`/email-push/${userId}/start`, formData, {
      timeout: 60000,
      headers: { 'Content-Type': 'multipart/form-data' },
    }))
  },

  // 查询最近邮箱拉取任务
  async getLatestEmailPushTask(userId) {
    return unwrap(await api.get(`/email-push/latest/${userId}`))
  },

  // 查询邮箱拉取任务状态
  async getEmailPushTaskStatus(jobId, userId = '') {
    return unwrap(await api.get(`/email-push/status/${jobId}`, {
      params: { user_id: userId || undefined },
    }))
  },
}

export default workbenchAPI
