import { useState, useRef, useEffect } from 'react'
import { Channel } from '../types'
import { useChannelStore } from '../stores/channelStore'
import { useAppStore } from '../stores/appStore'

interface Props {
  channel: Channel
  onClose: () => void
  onUploaded: (episodeId: number) => void
}

export default function UploadScriptModal({ channel, onClose, onUploaded }: Props) {
  const uploadScript = useChannelStore((s) => s.uploadScript)
  const pushToast = useAppStore((s) => s.pushToast)
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) {
      setError('Selecciona un archivo de guion')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const episode = await uploadScript(channel.id, file, title.trim() || undefined)
      pushToast?.('Guion cargado y episodio encolado', 'success')
      onUploaded(episode.id)
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al subir el guion')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
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

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">
              Título del episodio
            </label>
            <input
              ref={inputRef}
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Se usa la primera línea del archivo si lo dejas vacío"
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">
              Archivo de guion (.txt)
            </label>
            <input
              type="file"
              accept=".txt,text/plain"
              onChange={handleFileChange}
              className="block w-full text-sm text-slate-300 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-purple-600 file:text-white hover:file:bg-purple-500 file:cursor-pointer"
            />
            {file && (
              <p className="mt-2 text-xs text-slate-500">
                {(file.size / 1024).toFixed(1)} KB • {file.name}
              </p>
            )}
          </div>

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
              disabled={loading || !file}
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
