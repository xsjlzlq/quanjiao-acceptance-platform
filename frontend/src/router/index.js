import { createRouter, createWebHistory } from 'vue-router'
import axios from 'axios'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { public: true } },
  { path: '/tasks', name: 'Tasks', component: () => import('../views/Tasks.vue') },
  { path: '/score', name: 'Score', component: () => import('../views/ScoreBoard.vue') },
  { path: '/neiye', name: 'Neiye', component: () => import('../views/NeiyeForm.vue') },
  { path: '/settings', name: 'Settings', component: () => import('../views/Settings.vue') },
  { path: '/', name: 'Home', component: () => import('../views/Home.vue') },
  { path: '/waiye', name: 'Waiye', component: () => import('../views/WaiyeForm.vue') },
  { path: '/rectify', name: 'Rectify', component: () => import('../views/Rectify.vue') },
  { path: '/export', name: 'Export', component: () => import('../views/BatchExport.vue') }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 记录最近一次鉴权有效性检查时间戳，防止过于密集的路由重复调用
let lastAuthCheckTime = 0

// 路由守卫：未登录跳 /login；已登录则校验 Token 有效性与密码是否已被修改
router.beforeEach(async (to, from, next) => {
  const token = localStorage.getItem('auth_token')
  if (to.meta.public) {
    next()
    return
  }

  if (!token) {
    next('/login')
    return
  }

  // 若距离上次核验超过 30 秒或首次进入应用，向服务端校验 Token 是否依旧合法（防止旧密码旧设备免密直入）
  const now = Date.now()
  if (now - lastAuthCheckTime > 30000 || !from.name) {
    try {
      const res = await axios.get('/api/auth/check')
      if (res.data && res.data.code === 200) {
        lastAuthCheckTime = now
        // 同步最新的角色与权限信息
        if (res.data.perms) {
          localStorage.setItem('auth_perms', JSON.stringify(res.data.perms))
        }
        if (res.data.role) {
          localStorage.setItem('auth_role', res.data.role)
        }
        if (res.data.target_db) {
          localStorage.setItem('auth_target_db', res.data.target_db)
        }
        if (res.data.county_name) {
          localStorage.setItem('auth_county_name', res.data.county_name)
        }
        next()
      } else {
        throw new Error('凭证失效')
      }
    } catch (err) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_username')
      localStorage.removeItem('auth_role')
      localStorage.removeItem('auth_perms')
      localStorage.removeItem('auth_target_db')
      localStorage.removeItem('auth_county_name')
      next('/login')
    }
  } else {
    next()
  }
})

export default router