import { create } from 'zustand'
import { api } from '../api/client'
import { setAuthToken } from '../api/auth'

const STORAGE_KEY = 'podcast_studio_auth'

interface StoredAuth {
  token: string
  username: string
}

interface AuthState {
  token: string | null
  username: string | null
  isLoading: boolean
  error: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  init: () => void
  clearError: () => void
}

function readStoredAuth(): StoredAuth | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as StoredAuth
    if (parsed?.token && parsed?.username) return parsed
  } catch {
    // token corrupto
  }
  return null
}

function saveStoredAuth(auth: StoredAuth | null) {
  if (auth) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(auth))
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  username: null,
  isLoading: false,
  error: null,

  init: () => {
    const stored = readStoredAuth()
    if (stored) {
      setAuthToken(stored.token)
      set({ token: stored.token, username: stored.username })
    }
  },

  login: async (username: string, password: string) => {
    set({ isLoading: true, error: null })
    try {
      const response = await api.login(username, password)
      const auth: StoredAuth = { token: response.access_token, username }
      saveStoredAuth(auth)
      setAuthToken(response.access_token)
      set({ token: response.access_token, username, isLoading: false })
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error desconocido al iniciar sesión'
      set({ error: message, isLoading: false, token: null, username: null })
      saveStoredAuth(null)
      throw err
    }
  },

  logout: () => {
    saveStoredAuth(null)
    setAuthToken(null)
    set({ token: null, username: null, error: null })
  },

  clearError: () => set({ error: null }),
}))
