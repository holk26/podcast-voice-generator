import { useState, useRef, useEffect } from 'react'
import { Channel } from '../types'
import { useChannelStore } from '../stores/channelStore'
import { useAppStore } from '../stores/appStore'

type Mode = 'file' | 'text'

interface Props {
  channel: Channel
  onClose: () => void
  onUploaded: (episodeId: number) => void
}

export default function UploadScriptModal({ channel, onClose, onUploaded }: Props) {
  const uploadScript = useChannelStore((s) => s.uploadScript)
  const createFromText = useChannelStore((s) => s.createFromText)
  const pushToast = useAppStore((s) => s.pushToast)
  const [mode, setMode] = useState<Mode>('file')
  const [file, setFile] = useState<File | null>(null)
  const [sourceText, setSourceText] = useState('')
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0] ?? null
    setFile(selected)
    setError(null)
    if (selected && !title) {
      const base = selected.name.replace(/\.[^/.]+$/, '').replace(/[_-]/g, ' ')
      setTitle(base.slice(0, 120))
    }
  }

  const deriveTitleFromText = (text: string) => {
    const first = text.split('\n').find((l) => l.trim())?.trim() || ''
    return first.replace(/^#+\s*/, '').slice(0, 120)
  }

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value
    setSourceText(text)
    setError(null)
    if (!title) {
      setTitle(deriveTitleFromText(text))
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const episode =
        mode === 'file'
          ? await uploadScript(channel.id, file!, title.trim() || undefined)
          : await createFromText(channel.id, sourceText, title.trim() || undefined)
      pushToast('Guion cargado y episodio encolado', 'success')
      onUploaded(episode.id)
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al subir el guion')
    } finally {
      setLoading(false)
    }
  }

  const canSubmit =
    mode === 'file' ? Boolean(file) : sourceText.trim().length > 0

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700 shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-xl">📄</span>
            <h2 className="text-lg font-bold text-slate-100">Cargar guion en «{channel.name}»</h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors text-2xl leading-none"
            aria-label="Cerrar"
          >
            ×
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4 flex-1 min-h-0 flex flex-col">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">
              Título del episodio
            </label>
            <input
              ref={inputRef}
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Se usa la primera línea del texto si lo dejas vacío"
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>

          <div className="flex gap-2 border-b border-slate-700 pb-1">
            <button
              type="button"
              onClick={() => setMode('file')}
              className={`px-3 py-1.5 text-sm rounded-t-lg transition-colors ${
                mode === 'file'
                  ? 'text-purple-300 border-b-2 border-purple-500'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Subir archivo
            </button>
            <button
              type="button"
              onClick={() => {
                setMode('text')
                setTimeout(() => textareaRef.current?.focus(), 0)
              }}
              className={`px-3 py-1.5 text-sm rounded-t-lg transition-colors ${
                mode === 'text'
                  ? 'text-purple-300 border-b-2 border-purple-500'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Pegar / editar texto
            </button>
          </div>

          {mode === 'file' ? (
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">
                Archivo de guion (.txt o .md)
              </label>
              <input
                type="file"
                accept=".txt,.md,text/plain,text/markdown"
                onChange={handleFileChange}
                className="block w-full text-sm text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-purple-600 file:text-white hover:file:bg-purple-500 file:cursor-pointer"
              />
              {file && (
                <p className="mt-2 text-xs text-slate-500">
                  {(file.size / 1024).toFixed(1)} KB • {file.name}
                </p>
              )}
            </div>
          ) : (
            <div className="flex-1 min-h-0 flex flex-col">
              <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">
                Guion / Texto narrado
              </label>
              <textarea
                ref={textareaRef}
                value={sourceText}
                onChange={handleTextChange}
                rows={12}
                className="flex-1 min-h-[200px] w-full p-2 bg-slate-800 border border-slate-600 text-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500 text-sm font-mono leading-relaxed resize-none"
                placeholder="Pega o escribe el guion aquí. Puedes usar etiquetas de emoción como <|emotion:contemplation|>, <|prosody:pause|>, <|sfx:sigh|>..."
                spellCheck={false}
              />
              <p className="mt-1 text-xs text-slate-500">
                {sourceText.length.toLocaleString()} caracteres •{' '}
                {sourceText.trim() ? sourceText.trim().split(/\s+/).length.toLocaleString() : 0} palabras
              </p>
            </div>
          )}

          <div className="text-xs text-slate-500 bg-slate-800/50 border border-slate-700/50 rounded-lg p-3">
            <p className="font-medium text-slate-400 mb-1">Canal:</p>
            <p>{channel.niche || 'Sin nicho'} • voz {channel.default_voice_id} • {channel.target_minutes} min objetivo</p>
          </div>

          {error && (
            <div className="p-2 bg-red-500/10 border border-red-500/40 rounded-lg text-red-300 text-sm">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading || !canSubmit}
              className="px-4 py-2 text-sm bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {loading ? 'Subiendo...' : '🚀 Subir y encolar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
