// API 基础配置
const BASE_URL = 'http://localhost:8000/api'

// 请求封装
const request = (options) => {
  return new Promise((resolve, reject) => {
    const token = uni.getStorageSync('token')
    
    uni.request({
      url: BASE_URL + options.url,
      method: options.method || 'GET',
      data: options.data || {},
      header: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {})
      },
      success: (res) => {
        if (res.statusCode === 200 && res.data.success) {
          resolve(res.data)
        } else {
          uni.showToast({
            title: res.data.message || '请求失败',
            icon: 'none'
          })
          reject(res.data)
        }
      },
      fail: (err) => {
        console.error('请求错误:', err)
        uni.showToast({
          title: '网络错误',
          icon: 'none'
        })
        reject(err)
      }
    })
  })
}

// API 接口
export const api = {
  // 用户登录
  login(data) {
    return request({
      url: '/login',
      method: 'POST',
      data
    })
  },
  
  // 获取用户信息
  getUserInfo(userId) {
    return request({
      url: `/user/${userId}`,
      method: 'GET'
    })
  },
  
  // 获取发票列表
  getInvoices(page, limit, keyword = '') {
    return request({
      url: `/invoices?user_id=test&page=${page}&limit=${limit}&keyword=${keyword}`,
      method: 'GET'
    })
  },
  
  // 上传发票
  uploadInvoice(filePath) {
    return new Promise((resolve, reject) => {
      const token = uni.getStorageSync('token')
      
      uni.uploadFile({
        url: BASE_URL + '/upload/test',
        filePath: filePath,
        name: 'file',
        formData: {},
        header: {
          ...(token ? { 'Authorization': `Bearer ${token}` } : {})
        },
        success: (res) => {
          const data = JSON.parse(res.data)
          if (data.success) {
            resolve(data)
          } else {
            reject(data)
          }
        },
        fail: (err) => {
          reject(err)
        }
      })
    })
  },
  
  // 删除发票
  deleteInvoice(invoiceId) {
    return request({
      url: `/invoice/test/${invoiceId}`,
      method: 'DELETE'
    })
  },
  
  // OCR 识别（一键识别）
  recognizeInvoice() {
    return request({
      url: '/workbench/recognize-unrecognized',
      method: 'POST'
    })
  },
  
  // 获取识别任务状态
  getRecognizeStatus(jobId) {
    return request({
      url: `/workbench/recognize-status/${jobId}`,
      method: 'GET'
    })
  },
  
  // 重新识别单张发票
  retryInvoice(invoiceId) {
    return request({
      url: `/workbench/invoice/retry/${invoiceId}`,
      method: 'POST'
    })
  },
  
  // 获取统计信息
  getStats() {
    return request({
      url: '/stats/test',
      method: 'GET'
    })
  }
}

export default api
