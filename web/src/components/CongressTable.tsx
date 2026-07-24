import { useEffect, useMemo, useState } from 'react'
import { useChannelStore } from '../stores/channelStore'

interface AgentDef {
  id: string
  name: string
  emoji: string
  role: string
}

const AGENTS: Record<string, AgentDef> = {
  strategist: { id: 'strategist', name: 'Estratega', emoji: '🧠', role: 'Propone ideas' },
  critic: { id: 'critic', name: 'Editor Jefe', emoji: '🎩', role: 'Filtra y selecciona' },
  showrunner: { id: 'showrunner', name: 'Showrunner', emoji: '🎬', role: 'Diseña temporadas' },
  research: { id: 'research', name: 'Investigador', emoji: '🔍', role: 'Busca datos' },
  outline: { id: 'outline', name: 'Planificador', emoji: '🗺️', role: 'Estructura el episodio' },
  writer: { id: 'writer', name: 'Guionista', emoji: '✍️', role: 'Escribe secciones' },
  editor: { id: 'editor', name: 'Editor', emoji: '📝', role: 'Pule el guion' },
  voice_director: { id: 'voice_director', name: 'Dir. de Voz', emoji: '🎙️', role: 'Prepara para TTS' },
  director: { id: 'director', name: 'Director', emoji: '🎯', role: 'Supervisa y da el visto bueno' },
  translate: { id: 'translate', name: 'Traductor', emoji: '🌐', role: 'Corrige el idioma' },
  curator: { id: 'curator', name: 'Curador', emoji: '📚', role: 'Limpia el audiolibro' },
}

const ROSTER: Record<string, string[]> = {
  plan: ['strategist', 'critic'],
  season: ['showrunner'],
  script: ['research', 'outline', 'writer', 'editor', 'voice_director', 'director'],
  audiobook: ['curator'],
}

const KIND_TITLE: Record<string, string> = {
  plan: 'Mesa redonda: plan editorial',
  season: 'Mesa redonda: nueva temporada',
  script: 'Mesa redonda: escribiendo el guion',
  audiobook: 'Mesa redonda: curando audiolibro',
}

function stepToAgent(step: string): string | null {
  const base = step.replace(/_done$/, '')
  if (base === 'write_section') return 'writer'
  if (base === 'approved') return 'director'
  if (base === 'curate_chunk') return 'curator'
  return AGENTS[base] ? base : null
}

function formatSecs(secs: number) {
  if (secs < 60) return `${Math.round(secs)}s`
  return `${Math.floor(secs / 60)}m ${Math.round(secs % 60)}s`
}

function LiveTimer({ since }: { since: number }) {
  const [, setTick] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 1000)
    return () => clearInterval(id)
  }, [])
  return <span className="text-purple-200">{formatSecs(Date.now() / 1000 - since)}</span>
}

/** Mesa redonda del congreso: los agentes se personifican y trabajan en vivo. */
export default function CongressTable() {
  const { activeJob, clearJob } = useChannelStore()

  const { roster, working, done, lastEvent } = useMemo(() => {
    if (!activeJob) return { roster: [], working: null, done: new Set<string>(), lastEvent: null }
    const base = ROSTER[activeJob.kind] ?? []
    const rosterSet = new Set(base)
    const doneSet = new Set<string>()
    let workingAgent: string | null = null

    activeJob.events.forEach((e) => {
      const agentId = stepToAgent(e.step)
      if (!agentId) return
      rosterSet.add(agentId)
      if (e.step.endsWith('_done')) {
        doneSet.add(agentId)
        if (workingAgent === agentId) workingAgent = null
      } else {
        doneSet.delete(agentId)
        workingAgent = agentId
      }
    })
    return {
      roster: [...rosterSet],
      working: workingAgent,
      done: doneSet,
      lastEvent: activeJob.events[activeJob.events.length - 1] ?? null,
    }
  }, [activeJob])

  if (!activeJob) return null
  const running = activeJob.status === 'running'
  const failed = activeJob.status === 'error'
  const n = roster.length || 1

  return (
    <div className="mb-4 rounded-xl bg-gradient-to-b from-indigo-950 to-purple-950 p-5 text-white shadow-lg">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-bold text-lg">
          {KIND_TITLE[activeJob.kind] ?? 'Mesa redonda'}
          {running && <span className="ml-2 animate-pulse">●</span>}
          {activeJob.status === 'done' && ' ✓'}
        </h3>
        {!running && (
          <button type="button" onClick={clearJob} className="text-xs text-purple-300 hover:text-white">
            Cerrar
          </button>
        )}
      </div>

      {/* La mesa con los agentes alrededor */}
      <div className="relative mx-auto my-6 h-64 w-full max-w-xl">
        <div className="absolute left-1/2 top-1/2 h-28 w-56 -translate-x-1/2 -translate-y-1/2 rounded-[50%] bg-amber-900 shadow-inner border-4 border-amber-950" />
        {lastEvent && (
          <div className="absolute left-1/2 top-1/2 z-10 w-52 -translate-x-1/2 -translate-y-1/2 rounded-lg bg-white/95 p-2 text-center text-xs text-gray-800 shadow">
            {running ? (
              <>
                <span className="font-medium">{lastEvent.message}</span>
                <div className="mt-1">
                  <LiveTimer since={lastEvent.ts} />
                </div>
              </>
            ) : (
              <span className="font-medium">
                {failed ? `Error: ${activeJob.error ?? 'falló'}` : '¡Trabajo terminado! 🎉'}
              </span>
            )}
          </div>
        )}
        {roster.map((agentId, i) => {
          const agent = AGENTS[agentId]
          const angle = (2 * Math.PI * i) / n - Math.PI / 2
          const x = 50 + 44 * Math.cos(angle)
          const y = 50 + 44 * Math.sin(angle)
          const isWorking = working === agentId && running
          const isDone = done.has(agentId)
          return (
            <div
              key={agentId}
              className="absolute -translate-x-1/2 -translate-y-1/2 text-center transition-all duration-500"
              style={{ left: `${x}%`, top: `${y}%` }}
            >
              <div
                className={`mx-auto flex h-14 w-14 items-center justify-center rounded-full text-2xl transition-all duration-500 ${
                  isWorking
                    ? 'bg-purple-500 ring-4 ring-purple-300 animate-bounce scale-110 shadow-lg shadow-purple-500/50'
                    : isDone
                      ? 'bg-green-700 ring-2 ring-green-400'
                      : 'bg-indigo-800 opacity-60'
                }`}
                title={`${agent.name} — ${agent.role}`}
              >
                {agent.emoji}
                {isDone && !isWorking && (
                  <span className="absolute -right-1 -top-1 rounded-full bg-green-500 px-1 text-[10px]">✓</span>
                )}
              </div>
              <div className={`mt-1 text-[11px] font-medium ${isWorking ? 'text-purple-200' : 'text-purple-300/70'}`}>
                {agent.name}
              </div>
            </div>
          )
        })}
      </div>

      {/* Registro de la conversación */}
      <div className="max-h-56 overflow-y-auto rounded-lg bg-black/20 p-3">
        <ul className="space-y-2 text-sm">
          {activeJob.events.map((e, i) => {
            const agentId = stepToAgent(e.step)
            const agent = agentId ? AGENTS[agentId] : null
            return (
              <li key={i} className="flex gap-2">
                <span className="text-lg leading-5">{agent?.emoji ?? '⚙️'}</span>
                <div className="min-w-0">
                  <span className="text-purple-300">{agent?.name ?? 'Sistema'}:</span>{' '}
                  <span className="text-purple-100">{e.message}</span>
                  {e.content && (
                    <details className="mt-1">
                      <summary className="cursor-pointer text-xs text-purple-400 underline">
                        {e.step.endsWith('_done') ? 'ver salida' : 'ver prompt'}
                      </summary>
                      <pre className="mt-1 max-h-40 overflow-y-auto whitespace-pre-wrap rounded bg-black/30 p-2 text-xs text-purple-200">
                        {e.content}
                      </pre>
                    </details>
                  )}
                </div>
              </li>
            )
          })}
          {activeJob.events.length === 0 && (
            <li className="text-purple-300">La mesa se está reuniendo…</li>
          )}
        </ul>
      </div>
    </div>
  )
}
