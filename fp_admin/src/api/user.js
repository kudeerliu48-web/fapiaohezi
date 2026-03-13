/**
 * 用户管理 API：统一走 fp_api_new 管理端接口（见 api/admin.js）
 */
import { getUsersList as getUsersListAdmin, getUserDetail as getUserDetailAdmin, updateUser as updateUserAdmin, deleteUser as deleteUserAdmin, getUserStats as getUserStatsAdmin } from './admin'

export function getUsersList(page = 1, limit = 10) {
  return getUsersListAdmin(page, limit)
}

export function getUserDetail(userId) {
  return getUserDetailAdmin(userId)
}

export function updateUser(userId, data) {
  return updateUserAdmin(userId, data)
}

export function deleteUser(userId) {
  return deleteUserAdmin(userId)
}

export function getUserStats() {
  return getUserStatsAdmin()
}
