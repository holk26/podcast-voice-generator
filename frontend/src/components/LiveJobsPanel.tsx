import { useEffect, useRef, useState } from 'react'
import { api, sseUrl } from '../api/client'
import { CrewJobEvent, JobSummary } from '../types'

const KIND_LABEL: Record<string, string> = {
  plan: 'Plan editorial',
  script: 'Guion',
  season: 'Temporada',
  tts: 'Síntesis de voz',
  audiobook: 'Audiolibro',
}

interface JobState {
  summary: JobSummary
  events: CrewJobEvent[]
}

/** Panel de procesos en curso (congreso, síntesis) con eventos en vivo. */
export default function LiveJobsPanel() {
  const [jobs, setJobs] = useState<Record<string, JobState>>({})
  const sourcesRef = useRef<Map<string, EventSource>>(new Map())

  useEffect(() => {
    let cancelled = false

    const poll = async () => {
      let running: JobSummary[] = []
      try {
        running = await api.getJobs()
      } catch {
        return
      }
      if (cancelled) return

      const runningIds = new Set(running.map((j) => j.id))

      // Cierra streams de jobs que ya terminaron
      sourcesRef.current.forEach((source, id) => {
        if (!runningIds.has(id)) {
          source.close()
          sourcesRef.current.delete(id)
          // Muestra el estado final unos segundos más y luego se limpia
          setTimeout(() => {
            if (!cancelled) {
              setJobs((prev) => {
                const next = { ...prev }
                delete next[id]
                return next
              })
            }
          }, 8000)
        }
      })

      // Abre streams para jobs nuevos
      running.forEach((summary) => {
        if (sourcesRef.current.has(summary.id)) return
        setJobs((prev) => ({
          ...prev,
          [summary.id]: prev[summary.id] ?? { summary, events: [] },
        }))
        const source = new EventSource(sseUrl(`/jobs/${summary.id}/events`))
        sourcesRef.current.set(summary.id, source)
        source.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data)
            if (data.step === '__status__') {
              source.close()
              sourcesRef.current.delete(summary.id)
              return
            }
            const jobEvent = data as CrewJobEvent
            setJobs((prev) => {
              const current = prev[summary.id]
              if (!current) return prev
              return {
                ...prev,
                [summary.id]: { ...current, events: [...current.events, jobEvent] },
              }
            })
          } catch {
            // payload malformado
          }
        }
        source.onerror = () => {
          source.close()
          sourcesRef.current.delete(summary.id)
        }
      })
    }

    poll()
    const interval = setInterval(poll, 4000)
    return () => {
      cancelled = true
      clearInterval(interval)
      sourcesRef.current.forEach((s) => s.close())
      sourcesRef.current.clear()
    }
  }, [])

  const jobList = Object.values(jobs)
  if (jobList.length === 0) return null

  return (
    <div className="mb-6 space-y-3">
      <h3 className="text-lg font-bold tracking-tight">Procesos en curso</h3>
      {jobList.map(({ summary, events }) => (
        <div key={summary.id} className="bg-purple-500/10 border border-purple-500/40 rounded-xl p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="inline-block w-3 h-3 border-2 border-purple-400 border-t-transparent rounded-full animate-spin" />
            <strong className="text-sm text-slate-100">
              {KIND_LABEL[summary.kind] ?? summary.kind}: {summary.detail}
            </strong>
          </div>
          <ul className="space-y-1 text-sm text-slate-300 ml-5">
            {events.slice(-4).map((e, i, arr) => (
              <li key={i} className="flex items-center gap-2">
                {i === arr.length - 1 ? (
                  <span className="inline-block w-2 h-2 bg-purple-400 rounded-full animate-pulse" />
                ) : (
                  <span className="text-green-400">✓</span>
                )}
                <span>{e.message}</span>
              </li>
            ))}
            {events.length === 0 && (
              <li className="text-slate-400">Arrancando…</li>
            )}
          </ul>
        </div>
      ))}
    </div>
  )
}
