import { create } from 'zustand'

interface AppState {
  toast: string | null
  setToast: (message: string | null) => void
}

export const useAppStore = create<AppState>((set) => ({
  toast: null,
  setToast: (toast) => set({ toast }),
}))
