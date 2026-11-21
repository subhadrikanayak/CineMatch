import axios from 'axios'

const KEY = 'cinematch_token'

export const tokenStore = {
  get: () => localStorage.getItem(KEY),
  set: (t) => localStorage.setItem(KEY, t),
  clear: () => localStorage.removeItem(KEY),
}

// indexes: null -> ?language=ml&language=te (the format FastAPI expects for lists)
const api = axios.create({ baseURL: '/api/v1', paramsSerializer: { indexes: null } })

api.interceptors.request.use((cfg) => {
  const t = tokenStore.get()
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && tokenStore.get()) {
      tokenStore.clear()
      window.dispatchEvent(new Event('auth:logout'))
    }
    return Promise.reject(err)
  },
)

export function errorMessage(err) {
  const d = err.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => x.msg).join('. ')
  if (err.code === 'ERR_NETWORK') return 'Cannot reach the server. Is the backend running?'
  return err.message || 'Something went wrong'
}

export default api