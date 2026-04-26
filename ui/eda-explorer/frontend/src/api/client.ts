import axios, { type AxiosInstance } from 'axios'

/**
 * In dev, Vite proxies /api → http://127.0.0.1:8235 (FastAPI).
 * In any other host, override via VITE_API_BASE.
 */
const baseURL =
  (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'

export const api: AxiosInstance = axios.create({
  baseURL,
  timeout: 20_000,
  headers: { Accept: 'application/json' },
})

export const USE_MOCK = import.meta.env.VITE_USE_MOCK === '1'
