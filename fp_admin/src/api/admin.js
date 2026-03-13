/**
 * 管理端接口：对接 fp_api_new 的 /api/admin/* 与 main.db 用户（含会员信息）
 * 会员类型：normal 普通用户(10次) | monthly 月付(30天不限次) | yearly 年付(365天不限次)
 */
import request from '@/utils/request'

/** 获取用户列表（分页，含会员信息） */
export function getUsersList(page = 1, limit = 10) {
  return request({
    url: '/admin/users',
    method: 'get',
    params: { page, limit }
  })
}

/** 获取用户详情（含会员信息） */
export function getUserDetail(userId) {
  return request({
    url: `/admin/user/${userId}`,
    method: 'get'
  })
}

/** 更新用户（含会员信息：member_type, member_start_at, recognition_used） */
export function updateUser(userId, data) {
  return request({
    url: `/admin/user/${userId}`,
    method: 'put',
    data
  })
}

/** 删除用户 */
export function deleteUser(userId) {
  return request({
    url: `/admin/user/${userId}`,
    method: 'delete'
  })
}

/** 管理端统计 */
export function getUserStats() {
  return request({
    url: '/admin/stats',
    method: 'get'
  })
}
