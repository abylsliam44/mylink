import axios from 'axios'

const DEFAULT_API = 'http://localhost:8000'
const rawBase = import.meta.env.VITE_API_BASE || (window as any).__API_BASE__ || DEFAULT_API

export const API_BASE: string = String(rawBase)

export const api = axios.create({ baseURL: API_BASE, timeout: 30000 })

export function setAuthToken(token: string | null) {
  if (token) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`
  } else {
    delete api.defaults.headers.common['Authorization']
  }
}

export function persistAuthToken(token: string | null) {
  if (token) {
    localStorage.setItem('auth_token', token)
  } else {
    localStorage.removeItem('auth_token')
  }
  setAuthToken(token)
}

// Initialize from storage if present
try {
  const saved = localStorage.getItem('auth_token')
  if (saved) setAuthToken(saved)
} catch {}

export function wsUrl(path: string): string {
  const url = new URL(API_BASE)
  url.protocol = url.protocol.replace('http', 'ws')
  const p = path.startsWith('/') ? path : `/${path}`
  return `${url.origin}${p}`
}
