import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  withCredentials: true
})

api.interceptors.request.use(config => {
  config.headers['X-Session-Activity'] ||= '1'
  return config
})

api.interceptors.response.use(
  response => response,
  error => {
    if (error?.response?.status === 401 && !error.config?.url?.includes('/auth/login')) {
      localStorage.removeItem('active_menu')
      localStorage.removeItem('opened_tabs')
      window.dispatchEvent(new CustomEvent('session-expired'))
    }
    return Promise.reject(error)
  }
)

export type User = {
  id: number
  username: string
  real_name: string
  role: string
  role_name?: string
  menus?: string[]
  status: 'active' | 'disabled'
}
