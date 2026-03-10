import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('user')
      localStorage.removeItem('token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export const authAPI = {
  // 兼容旧调用
  login(data) {
    return this.loginByPassword(data)
  },

  loginByPassword(data) {
    return api.post('/auth/login-by-password', data)
  },

  loginBySMS(data) {
    return api.post('/auth/login-by-sms', data)
  },

  sendSMSCode(data) {
    return api.post('/auth/send-sms-code', data)
  },

  register(data) {
    return api.post('/auth/register', data)
  },

  getUserInfo(userId) {
    return api.get(`/user/${userId}`)
  },

  updateUserInfo(userId, data) {
    return api.put(`/user/${userId}`, data)
  },

  logout() {
    localStorage.removeItem('user')
    localStorage.removeItem('token')
    return Promise.resolve({ success: true })
  },
}

export default api
