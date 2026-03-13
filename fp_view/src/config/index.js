// 前端统一接口配置
// 优先读取环境变量 VUE_APP_API_BASE_URL，没有则回退到本地开发地址

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000'

export default {
  API_BASE_URL,
  API_PREFIX: `${API_BASE_URL}/api`,
}

