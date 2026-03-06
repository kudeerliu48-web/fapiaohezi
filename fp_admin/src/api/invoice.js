import request from '@/utils/request'

// 获取所有发票列表（管理员）
export function getAllInvoices(page = 1, limit = 10, keyword = '') {
  return request({
    url: `/admin/invoices?page=${page}&limit=${limit}&keyword=${keyword}`,
    method: 'get'
  })
}

// 获取发票详情
export function getInvoiceDetail(invoiceId) {
  return request({
    url: `/invoice/detail/${invoiceId}`,
    method: 'get'
  })
}

// 上传发票文件
export function uploadInvoice(file, userId) {
  const formData = new FormData()
  formData.append('file', file)
  return request({
    url: `/upload/${userId}`,
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

// 删除发票
export function deleteInvoice(invoiceId) {
  return request({
    url: `/invoice/${invoiceId}`,
    method: 'delete'
  })
}

// 获取发票统计
export function getInvoiceStats() {
  return request({
    url: '/admin/invoice-stats',
    method: 'get'
  })
}

// 导出发票
export function exportInvoices(keyword = '') {
  return request({
    url: `/admin/invoices/export?keyword=${keyword}`,
    method: 'get',
    responseType: 'blob'
  })
}
