import axios from 'axios'

// 创建axios实例
const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 在发送请求之前做些什么
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => {
    // 对请求错误做些什么
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  response => {
    // 对响应数据做点什么
    return response
  },
  error => {
    // 对响应错误做点什么
    if (error.response) {
      switch (error.response.status) {
        case 401:
          // 未授权，跳转到登录页
          localStorage.removeItem('user')
          localStorage.removeItem('token')
          window.location.href = '/login'
          break
        case 403:
          // 禁止访问
          console.error('禁止访问')
          break
        case 404:
          // 未找到
          console.error('请求的资源不存在')
          break
        case 500:
          // 服务器错误
          console.error('服务器内部错误')
          break
      }
    } else if (error.request) {
      // 请求已发出但没有收到响应
      console.error('网络错误，请检查网络连接')
    } else {
      // 其他错误
      console.error('请求配置错误')
    }
    return Promise.reject(error)
  }
)

// 认证相关API
export const authAPI = {
  // 用户登录
  login(data) {
    return api.post('/login', data)
  },
  
  // 用户注册
  register(data) {
    return api.post('/register', data)
  },
  
  // 获取用户信息
  getUserInfo(userId) {
    return api.get(`/user/${userId}`)
  },
  
  // 更新用户信息
  updateUserInfo(userId, data) {
    return api.put(`/user/${userId}`, data)
  },
  
  // 用户登出
  logout() {
    localStorage.removeItem('user')
    localStorage.removeItem('token')
    return Promise.resolve({ success: true })
  }
}

export default api
