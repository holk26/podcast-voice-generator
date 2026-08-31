import { useEffect } from 'react'
import { useAppStore } from '../stores/appStore'

export default function ConfirmDialog() {
  const confirm = useAppStore((s) => s.confirm)
  const resolveConfirm = useAppStore((s) => s.resolveConfirm)

  useEffect(() => {
    if (!confirm) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') resolveConfirm(false)
      if (e.key === 'Enter') resolveConfirm(true)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [confirm, resolveConfirm])

  if (!confirm) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-title"
      onClick={() => resolveConfirm(false)}
    >
      <div
        className="bg-slate-800 border border-slate-600 rounded-xl shadow-2xl max-w-sm w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h3
          id="confirm-title"
          className="text-lg font-bold text-slate-100 mb-2"
        >
          {confirm.title}
        </h3>
        <p className="text-sm text-slate-400 mb-6">{confirm.message}</p>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={() => resolveConfirm(false)}
            className="px-4 py-2 rounded-lg text-sm font-medium text-slate-300 bg-slate-700 hover:bg-slate-600 transition-colors"
            autoFocus
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={() => resolveConfirm(true)}
            className={`px-4 py-2 rounded-lg text-sm font-medium text-white transition-colors ${
              confirm.danger
                ? 'bg-red-600 hover:bg-red-500'
                : 'bg-purple-600 hover:bg-purple-500'
            }`}
          >
            {confirm.confirmLabel ?? 'Confirmar'}
          </button>
        </div>
      </div>
    </div>
  )
}
