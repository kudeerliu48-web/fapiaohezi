import request from '@/utils/request'

// 获取所有用户列表
export function getUsersList(page = 1, limit = 10) {
  return request({
    url: `/admin/users?page=${page}&limit=${limit}`,
    method: 'get'
  })
}

// 获取用户详情
export function getUserDetail(userId) {
  return request({
    url: `/user/${userId}`,
    method: 'get'
  })
}

// 删除用户
export function deleteUser(userId) {
  return request({
    url: `/admin/user/${userId}`,
    method: 'delete'
  })
}

// 获取用户统计信息
export function getUserStats() {
  return request({
    url: '/admin/stats',
    method: 'get'
  })
}
