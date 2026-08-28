import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { public: true } },
  { path: '/tasks', name: 'Tasks', component: () => import('../views/Tasks.vue') },
  { path: '/score', name: 'Score', component: () => import('../views/ScoreBoard.vue') },
  { path: '/neiye', name: 'Neiye', component: () => import('../views/NeiyeForm.vue') },
  { path: '/settings', name: 'Settings', component: () => import('../views/Settings.vue') },
  { path: '/', name: 'Home', component: () => import('../views/Home.vue') },
  { path: '/waiye', name: 'Waiye', component: () => import('../views/WaiyeForm.vue') },
  { path: '/rectify', name: 'Rectify', component: () => import('../views/Rectify.vue') }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：未登录跳 /login
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('auth_token')
  if (!to.meta.public && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router