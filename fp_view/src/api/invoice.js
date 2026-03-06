import api from './auth'

// 发票相关API
export const invoiceAPI = {
  // 上传文件
  uploadFile(userId, file) {
    const formData = new FormData()
    formData.append('file', file)
    
    return api.post(`/upload/${userId}`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },
  
  // 获取发票列表
  getInvoices(userId, page = 1, limit = 10, keyword = '', recognizedOnly = false) {
    return api.get(`/invoices/${userId}`, {
      params: {
        page,
        limit,
        keyword: keyword ? keyword : undefined,
        recognized_only: recognizedOnly ? true : undefined
      }
    })
  },
  
  // 获取发票详情
  getInvoiceDetail(userId, invoiceId) {
    return api.get(`/invoice/${userId}/${invoiceId}`)
  },
  
  // 手动OCR识别
  processOCR(userId, invoiceId) {
    return api.post(`/ocr/${userId}/${invoiceId}`)
  },

  // 识别所有未识别发票（外部批处理）
  recognizeUnrecognized(userId) {
    return api.post(`/recognize/${userId}/unrecognized`)
  },

  // 查询识别任务状态
  getRecognizeStatus(jobId) {
    return api.get(`/recognize/status/${jobId}`)
  },

  // 邮箱推送：启动任务
  startEmailPush(userId, payload) {
    const formData = new FormData()
    formData.append('range_key', payload.rangeKey)
    if (payload.mailbox) formData.append('mailbox', payload.mailbox)
    formData.append('auth_code', payload.authCode)

    return api.post(`/email-push/${userId}/start`, formData, {
      timeout: 60000,
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  },

  // 邮箱推送：查询状态
  getEmailPushStatus(jobId) {
    return api.get(`/email-push/status/${jobId}`, {
      timeout: 30000,
    })
  },
  
  // 获取用户统计信息
  getUserStats(userId) {
    return api.get(`/stats/${userId}`)
  },

  // 删除单张发票
  deleteInvoice(userId, invoiceId) {
    return api.delete(`/invoice/${userId}/${invoiceId}`)
  },

  // 批量删除发票
  batchDeleteInvoices(userId, invoiceIds) {
    return api.post(`/invoices/${userId}/batch-delete`, {
      invoice_ids: invoiceIds
    })
  },

  // 导出Excel
  exportInvoicesExcel(userId, keyword = '') {
    return api.get(`/invoices/${userId}/export`, {
      params: keyword ? { keyword } : {},
      responseType: 'blob'
    })
  }
}

export default invoiceAPI
