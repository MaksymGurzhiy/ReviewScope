// Thin axios wrapper that injects the Supabase access token automatically.
import axios from 'axios'
import { supabase } from './supabase'

const root = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const baseURL = root.replace(/\/+$/, '') + '/api'

export const api = axios.create({ baseURL, timeout: 600000 })

api.interceptors.request.use(async (config) => {
  const { data } = await supabase.auth.getSession()
  const token = data?.session?.access_token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err?.response?.data?.detail
    if (detail && err.message) {
      err.message = typeof detail === 'string' ? detail : JSON.stringify(detail)
    }
    return Promise.reject(err)
  }
)

export default api
