import { useEffect, useState } from 'react'
import { useChannelStore } from '../stores/channelStore'
import { CrewJobEvent } from '../types'

const KIND_LABEL: Record<string, string> = {
  plan: 'Generando plan editorial',
  script: 'Generando guion',
  season: 'Diseñando temporada',
}

function isPrompt(step: string) {
  return !step.endsWith('_done') && step !== 'parse' && step !== 'done'
}

function formatSecs(secs: number) {
  if (secs < 60) return `${Math.round(secs)}s`
  return `${Math.floor(secs / 60)}m ${Math.round(secs % 60)}s`
}

/** Cronómetro del paso en curso (se actualiza cada segundo). */
function LiveTimer({ since }: { since: number }) {
  const [, setTick] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000)
    return () => clearInterval(id)
  }, [])
  return <span className="text-xs text-purple-300 ml-1">{formatSecs(Date.now() / 1000 - since)}</span>
}

function EventRow({ event, running, isLast, prevTs }: {
  event: CrewJobEvent
  running: boolean
  isLast: boolean
  prevTs?: number
}) {
  const icon =
    running && isLast ? (
      <span className="inline-block w-3 h-3 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
    ) : (
      <span className="text-green-400">✓</span>
    )
  const elapsed = prevTs ? event.ts - prevTs : null

  const summary = (
    <>
      {icon}
      <span>{event.message}</span>
      {running && isLast ? (
        <LiveTimer since={event.ts} />
      ) : (
        elapsed !== null && elapsed > 1 && (
          <span className="text-xs text-slate-500">+{formatSecs(elapsed)}</span>
        )
      )}
    </>
  )

  if (!event.content) {
    return <span className="flex items-center gap-2">{summary}</span>
  }

  return (
    <details className="group">
      <summary className="flex items-center gap-2 cursor-pointer hover:text-purple-300 list-none">
        {summary}
        <span className="text-xs text-purple-400 underline">
          {isPrompt(event.step) ? 'ver prompt' : 'ver salida'}
        </span>
      </summary>
      <pre className="mt-1 ml-5 p-2 bg-slate-950/70 border border-slate-700 rounded-lg text-xs text-slate-300 whitespace-pre-wrap max-h-64 overflow-y-auto">
        {event.content}
      </pre>
    </details>
  )
}

/** Muestra en tiempo real lo que hace el congreso de agentes (SSE). */
export default function CrewJobActivity() {
  const { activeJob, clearJob } = useChannelStore()
  if (!activeJob) return null

  const running = activeJob.status === 'running'
  const failed = activeJob.status === 'error'

  return (
    <div
      className={`p-4 rounded-xl border mb-4 ${
        failed
          ? 'bg-red-500/10 border-red-500/40'
          : running
            ? 'bg-purple-500/10 border-purple-500/40'
            : 'bg-green-500/10 border-green-500/40'
      }`}
    >
      <div className="flex justify-between items-center mb-2">
        <strong className="text-slate-100">
          {KIND_LABEL[activeJob.kind] ?? 'Trabajando'}
          {running && '…'}
          {activeJob.status === 'done' && ' ✓'}
          {failed && ' — error'}
        </strong>
        {!running && (
          <button
            type="button"
            onClick={clearJob}
            className="text-sm text-slate-400 hover:text-slate-200 transition-colors"
          >
            Cerrar
          </button>
        )}
      </div>
      <ul className="space-y-1 text-sm text-slate-300">
        {activeJob.events.map((e, i) => (
          <li key={i}>
            <EventRow
              event={e}
              running={running}
              isLast={i === activeJob.events.length - 1}
              prevTs={i > 0 ? activeJob.events[i - 1].ts : undefined}
            />
          </li>
        ))}
        {activeJob.events.length === 0 && (
          <li className="flex items-center gap-2 text-slate-400">
            <span className="inline-block w-3 h-3 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
            <span>Arrancando el congreso de agentes…</span>
          </li>
        )}
      </ul>
      {failed && activeJob.error && (
        <p className="text-sm text-red-400 mt-2">{activeJob.error}</p>
      )}
    </div>
  )
}
