import { useAppStore, type ToastKind } from '../stores/appStore'

const kindStyles: Record<ToastKind, string> = {
  success: 'bg-emerald-600/90 border-emerald-400',
  error: 'bg-red-600/90 border-red-400',
  info: 'bg-slate-700/95 border-slate-500',
}

const kindIcon: Record<ToastKind, string> = {
  success: '✓',
  error: '!',
  info: 'i',
}

export default function ToastHost() {
  const toasts = useAppStore((s) => s.toasts)
  const dismiss = useAppStore((s) => s.dismissToast)

  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm"
      role="region"
      aria-label="Notificaciones"
      aria-live="polite"
    >
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-start gap-3 px-4 py-3 rounded-lg border shadow-lg text-white text-sm ${kindStyles[t.kind]} animate-[fadeIn_0.15s_ease-out]`}
          role="status"
        >
          <span
            className="shrink-0 w-5 h-5 rounded-full bg-white/20 flex items-center justify-center text-xs font-bold"
            aria-hidden="true"
          >
            {kindIcon[t.kind]}
          </span>
          <span className="flex-1">{t.text}</span>
          <button
            type="button"
            onClick={() => dismiss(t.id)}
            className="shrink-0 text-white/70 hover:text-white text-lg leading-none"
            aria-label="Cerrar notificación"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
