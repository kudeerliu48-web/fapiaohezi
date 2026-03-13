import Vue from 'vue'
import VueRouter from 'vue-router'
import Login from '@/views/Login.vue'
import Profile from '@/views/Profile.vue'
import Invoice from '@/views/Invoice.vue'
import Recharge from '@/views/Recharge.vue'
import MainLayout from '@/views/MainLayout.vue'

Vue.use(VueRouter)

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: {
      title: '登录',
      requiresAuth: false,
    },
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
          title: '个人资料',
          requiresAuth: true,
        },
      },
    ],
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
          requiresAuth: true,
        },
      },
    ],
  },
  {
    path: '/recharge',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'Recharge',
        component: Recharge,
        meta: {
          title: '会员充值',
          requiresAuth: true,
        },
      },
    ],
  },
]

const router = new VueRouter({
  mode: 'history',
  base: process.env.BASE_URL,
  routes,
})

router.beforeEach((to, from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - 发票盒子`
  }

  const requiresAuth = to.matched.some((record) => record.meta.requiresAuth)
  const user = JSON.parse(localStorage.getItem('user') || 'null')

  if (requiresAuth && !user) {
    next('/login')
  } else if (to.path === '/login' && user) {
    next('/invoice')
  } else {
    next()
  }
})

export default router
