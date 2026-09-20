import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { createPinia } from 'pinia'
import Vant from 'vant'
import 'vant/lib/index.css'
import axios from 'axios'

// 配置 Axios 全局拦截器：统一在请求头中附带用户身份 Token 与账号标识，保障审计日志追溯，并带上工作数据库标识
axios.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  const username = localStorage.getItem('auth_username')
  const targetDb = localStorage.getItem('auth_target_db')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  if (username) {
    config.headers['X-Username'] = encodeURIComponent(username)
  }
  if (targetDb) {
    config.headers['X-Database'] = encodeURIComponent(targetDb)
  }
  return config
}, (error) => {
  return Promise.reject(error)
})

// 配置 Axios 响应拦截器：当服务端返回 401（Token过期、无效或密码被修改），立即强制清空本地缓存并踢回登录页
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_username')
      localStorage.removeItem('auth_role')
      localStorage.removeItem('auth_perms')
      localStorage.removeItem('auth_target_db')
      localStorage.removeItem('auth_county_name')
      if (router.currentRoute.value.path !== '/login') {
        router.push('/login')
      }
    }
    return Promise.reject(error)
  }
)

const app = createApp(App)

app.use(createPinia())
app.use(router)
app.use(Vant)

app.mount('#app')
