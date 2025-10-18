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

// Role persistence
const ROLE_KEY = 'auth_role'
export type UserRole = 'employer' | 'candidate'
const CANDIDATE_ID_KEY = 'candidate_id'

export function getRole(): UserRole | null {
  try {
    const v = localStorage.getItem(ROLE_KEY)
    return v === 'employer' || v === 'candidate' ? v : null
  } catch {
    return null
  }
}

export function setRole(role: UserRole | null) {
  try {
    if (role) localStorage.setItem(ROLE_KEY, role)
    else localStorage.removeItem(ROLE_KEY)
  } catch {}
}

export function logoutAll() {
  try {
    localStorage.removeItem('auth_token')
    localStorage.removeItem(ROLE_KEY)
    localStorage.removeItem(CANDIDATE_ID_KEY)
  } catch {}
  setAuthToken(null)
}

export function setCandidateId(id: string | null) {
  try {
    if (id) localStorage.setItem(CANDIDATE_ID_KEY, id)
    else localStorage.removeItem(CANDIDATE_ID_KEY)
  } catch {}
}

export function getCandidateId(): string | null {
  try {
    return localStorage.getItem(CANDIDATE_ID_KEY)
  } catch { return null }
}
