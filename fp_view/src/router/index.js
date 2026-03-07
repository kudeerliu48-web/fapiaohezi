import Vue from 'vue'
import VueRouter from 'vue-router'
import Login from '@/views/Login.vue'
import Profile from '@/views/Profile.vue'
import Invoice from '@/views/Invoice.vue'
import MainLayout from '@/views/MainLayout.vue'

Vue.use(VueRouter)

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: {
      title: '登录',
      requiresAuth: false
    }
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'Profile',
        component: Profile,
        meta: {
          title: '个人信息',
          requiresAuth: true
        }
      }
    ]
  },
  {
    path: '/invoice',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'Invoice',
        component: Invoice,
        meta: {
          title: '发票工作台',
          requiresAuth: true
        }
      }
    ]
  }
]

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - 发票盒子`
  }
  
  // 检查是否需要登录
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth)
  const user = JSON.parse(localStorage.getItem('user'))
  
  if (requiresAuth && !user) {
    // 需要登录但用户未登录，跳转到登录页
    next('/login')
  } else if (to.path === '/login' && user) {
    // 已登录用户访问登录页，跳转到首页
    next('/')
  } else {
    next()
  }
})

export default router
