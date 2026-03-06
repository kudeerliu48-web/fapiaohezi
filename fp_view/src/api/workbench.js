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
    return unwrap(await api.post(`/workbench/invoice/${userId}/${invoiceId}/retry`))
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
}

export default workbenchAPI

