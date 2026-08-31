import { create } from 'zustand'

export type ToastKind = 'success' | 'error' | 'info'

export interface ToastMessage {
  id: number
  kind: ToastKind
  text: string
}

export interface ConfirmRequest {
  title: string
  message: string
  confirmLabel?: string
  danger?: boolean
  resolve: (ok: boolean) => void
}

interface AppState {
  toasts: ToastMessage[]
  pushToast: (text: string, kind?: ToastKind) => void
  dismissToast: (id: number) => void
  confirm: ConfirmRequest | null
  askConfirm: (req: Omit<ConfirmRequest, 'resolve'>) => Promise<boolean>
  resolveConfirm: (ok: boolean) => void
}

let toastSeq = 0

export const useAppStore = create<AppState>((set, get) => ({
  toasts: [],
  confirm: null,

  pushToast: (text, kind = 'info') => {
    const id = ++toastSeq
    set((s) => ({ toasts: [...s.toasts, { id, kind, text }] }))
    window.setTimeout(() => get().dismissToast(id), 4000)
  },

  dismissToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  askConfirm: (req) =>
    new Promise<boolean>((resolve) => {
      set({ confirm: { ...req, resolve } })
    }),

  resolveConfirm: (ok) => {
    const c = get().confirm
    if (c) c.resolve(ok)
    set({ confirm: null })
  },
}))
