import { useChannelStore } from '../stores/channelStore'

const KIND_LABEL: Record<string, string> = {
  plan: 'Generando plan editorial',
  script: 'Generando guion',
  season: 'Diseñando temporada',
}

/** Muestra en tiempo real lo que hace el congreso de agentes (SSE). */
export default function CrewJobActivity() {
  const { activeJob, clearJob } = useChannelStore()
  if (!activeJob) return null

  const running = activeJob.status === 'running'
  const failed = activeJob.status === 'error'

  return (
    <div
      className={`p-4 rounded border mb-4 ${
        failed
          ? 'bg-red-50 border-red-300'
          : running
            ? 'bg-purple-50 border-purple-300'
            : 'bg-green-50 border-green-300'
      }`}
    >
      <div className="flex justify-between items-center mb-2">
        <strong>
          {KIND_LABEL[activeJob.kind] ?? 'Trabajando'}
          {running && '…'}
          {activeJob.status === 'done' && ' ✓'}
          {failed && ' — error'}
        </strong>
        {!running && (
          <button
            type="button"
            onClick={clearJob}
            className="text-sm text-gray-500 hover:text-gray-700"
          >
            Cerrar
          </button>
        )}
      </div>
      <ul className="space-y-1 text-sm">
        {activeJob.events.map((e, i) => {
          const isLast = i === activeJob.events.length - 1
          const icon =
            running && isLast ? (
              <span className="inline-block w-3 h-3 border-2 border-purple-600 border-t-transparent rounded-full animate-spin" />
            ) : (
              <span className="text-green-600">✓</span>
            )
          return (
            <li key={i}>
              {e.content ? (
                <details className="group">
                  <summary className="flex items-center gap-2 cursor-pointer hover:text-purple-800">
                    {icon}
                    <span>{e.message}</span>
                    <span className="text-xs text-gray-400 group-open:rotate-90 transition-transform">
                      ▶
                    </span>
                  </summary>
                  <pre className="mt-1 ml-5 p-2 bg-white/70 border rounded text-xs whitespace-pre-wrap max-h-64 overflow-y-auto">
                    {e.content}
                  </pre>
                </details>
              ) : (
                <span className="flex items-center gap-2">
                  {icon}
                  <span>{e.message}</span>
                </span>
              )}
            </li>
          )
        })}
        {activeJob.events.length === 0 && (
          <li className="flex items-center gap-2 text-gray-500">
            <span className="inline-block w-3 h-3 border-2 border-purple-600 border-t-transparent rounded-full animate-spin" />
            <span>Arrancando el congreso de agentes…</span>
          </li>
        )}
      </ul>
      {failed && activeJob.error && (
        <p className="text-sm text-red-700 mt-2">{activeJob.error}</p>
      )}
    </div>
  )
}
