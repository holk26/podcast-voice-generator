import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { api, sseUrl } from '../api/client'
import { Channel } from '../types'

type Step = 'source' | 'progress' | 'edit'

interface JobEvent {
  step: string
  message: string
  status?: string
  error?: string | null
  result?: { script_text?: string; title?: string; word_count?: number }
}

export default function GenerateScriptWizard({ channel, onClose }: { channel: Channel; onClose: () => void }) {
  const navigate = useNavigate()
  const [step, setStep] = useState<Step>('source')
  const [file, setFile] = useState<File | null>(null)
  const [pasted, setPasted] = useState('')
  const [title, setTitle] = useState('')
  const [events, setEvents] = useState<{ step: string; message: string }[]>([])
  const [jobError, setJobError] = useState<string | null>(null)
  const [script, setScript] = useState('')
  const [scriptTitle, setScriptTitle] = useState('')
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const esRef = useRef<EventSource | null>(null)

  const source = file ? file.name : pasted.trim() ? 'texto pegado' : ''
  const wordCount = useMemo(
    () => (script.trim() ? script.trim().split(/\s+/).length : 0),
    [script]
  )

  useEffect(() => () => esRef.current?.close(), [])

  const startJob = async () => {
    setJobError(null)
    setEvents([])
    try {
      const { job_id } = await api.startScriptJob(channel.id, {
        file: file ?? undefined,
        text: !file && pasted.trim() ? pasted : undefined,
        title: title.trim() || undefined,
      })
      setStep('progress')
      const es = new EventSource(sseUrl(`/jobs/${job_id}/events`))
      esRef.current = es
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as JobEvent
          if (data.step === '__status__') {
            es.close()
            if (data.status === 'done' && data.result?.script_text) {
              setScript(data.result.script_text)
              setScriptTitle(title.trim() || data.result.title || '')
              setStep('edit')
            } else {
              setJobError(data.error || 'El congreso no devolvió guion')
            }
          } else {
            setEvents((prev) => [...prev, { step: data.step, message: data.message }])
          }
        } catch {
          // payload malformado: ignorar
        }
      }
      es.onerror = () => {
        es.close()
        setJobError('Conexión con el job perdida')
      }
    } catch (err) {
      setJobError(err instanceof Error ? err.message : 'No se pudo lanzar el congreso')
    }
  }

  const handleCreate = async () => {
    setCreating(true)
    setCreateError(null)
    try {
      const episode = await api.createFromText(channel.id, script, scriptTitle.trim() || undefined)
      onClose()
      navigate({ to: '/queue', search: { highlight: episode.id } })
    } catch (err) {
      setCreateError(err instanceof Error ? err.message : 'No se pudo crear el episodio')
      setCreating(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget && step !== 'progress') onClose() }}
    >
      <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700 shrink-0">
          <h2 className="text-lg font-bold text-slate-100">Generar guion con IA — {channel.name}</h2>
          {step !== 'progress' && (
            <button onClick={onClose} className="text-slate-400 hover:text-white text-2xl leading-none" aria-label="Cerrar">×</button>
          )}
        </div>

        {step === 'source' && (
          <div className="p-5 space-y-4 overflow-y-auto">
            <label className="block">
              <span className="text-sm text-slate-400">Título (opcional)</span>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="mt-1 w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="El caso que vas a contar..."
              />
            </label>
            <div>
              <span className="text-sm text-slate-400">Materia prima (.txt o .md)</span>
              <input
                type="file"
                accept=".txt,.md,text/plain,text/markdown"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                className="mt-1 block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-slate-700 file:text-slate-100 hover:file:bg-slate-600"
              />
            </div>
            <div className="text-center text-slate-500 text-sm">— o pega el texto —</div>
            <textarea
              value={pasted}
              onChange={(e) => setPasted(e.target.value)}
              rows={8}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="Pega aquí notas, transcripciones, artículos..."
            />
            {jobError && (
              <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg">{jobError}</div>
            )}
            <div className="flex justify-end gap-2">
              <button onClick={onClose} className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg hover:bg-slate-600 transition-colors">
                Cancelar
              </button>
              <button
                onClick={startJob}
                disabled={!file && !pasted.trim()}
                className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Lanzar congreso 🎬
              </button>
            </div>
          </div>
        )}

        {step === 'progress' && (
          <div className="p-5 overflow-y-auto">
            <p className="text-sm text-slate-300 mb-3">
              El congreso está trabajando sobre «{source}». Puede tardar varios minutos.
            </p>
            <div className="space-y-1">
              {events.map((ev, i) => (
                <div key={i} className="text-sm text-slate-300 flex gap-2">
                  <span className="text-purple-400">✓</span>
                  <span>{ev.message}</span>
                </div>
              ))}
              <div className="text-sm text-slate-400 flex gap-2">
                <span className="animate-pulse">●</span>
                <span>trabajando…</span>
              </div>
            </div>
            {jobError && (
              <div className="mt-4 bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg">
                {jobError}
                <div className="flex gap-2 mt-3">
                  <button onClick={() => setStep('source')} className="bg-slate-700 text-slate-100 px-3 py-1 rounded-lg text-sm hover:bg-slate-600">
                    Volver y reintentar
                  </button>
                  <button onClick={onClose} className="bg-slate-700 text-slate-100 px-3 py-1 rounded-lg text-sm hover:bg-slate-600">
                    Descartar
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {step === 'edit' && (
          <div className="flex-1 min-h-0 flex flex-col p-5 gap-3 overflow-hidden">
            <input
              type="text"
              value={scriptTitle}
              onChange={(e) => setScriptTitle(e.target.value)}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
              placeholder="Título del episodio"
            />
            <textarea
              value={script}
              onChange={(e) => setScript(e.target.value)}
              className="flex-1 min-h-[40vh] w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 text-sm font-mono leading-relaxed focus:outline-none focus:ring-2 focus:ring-purple-500"
              spellCheck={false}
            />
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <span className="text-xs text-slate-500">
                {wordCount.toLocaleString()} palabras · ~{Math.max(1, Math.round(wordCount / 140))} min
              </span>
              <div className="flex gap-2">
                <button onClick={() => setStep('source')} className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg hover:bg-slate-600 transition-colors">
                  Regenerar
                </button>
                <button onClick={onClose} className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg hover:bg-slate-600 transition-colors">
                  Descartar
                </button>
                <button
                  onClick={handleCreate}
                  disabled={creating || !script.trim()}
                  className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50"
                >
                  {creating ? 'Creando…' : 'Crear episodio'}
                </button>
              </div>
            </div>
            {createError && (
              <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg">{createError}</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
