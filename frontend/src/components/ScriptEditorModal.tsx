import { useState, useEffect, useRef } from 'react'
import { Episode } from '../types'
import { useEpisodeStore } from '../stores/episodeStore'
import ScriptTextarea, { ScriptTextareaHandle } from './ScriptTextarea'

interface Props {
  episode: Episode
  onClose: () => void
}

export default function ScriptEditorModal({ episode, onClose }: Props) {
  const updateEpisode = useEpisodeStore((s) => s.updateEpisode)
  const retryEpisode = useEpisodeStore((s) => s.retryEpisode)
  const [text, setText] = useState(episode.source_text || '')
  const [title, setTitle] = useState(episode.title)
  const [description, setDescription] = useState(episode.description || '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const editorRef = useRef<ScriptTextareaHandle>(null)

  useEffect(() => {
    editorRef.current?.focus()
  }, [])

  // Close on Escape
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [onClose])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      await updateEpisode(episode.id, { title, source_text: text, description })
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al guardar')
    } finally {
      setSaving(false)
    }
  }

  const handleSaveAndRetry = async () => {
    setSaving(true)
    setError(null)
    try {
      await updateEpisode(episode.id, { title, source_text: text, description })
      await retryEpisode(episode.id)
      onClose()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error al guardar o reintentar')
      setSaving(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700 shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-xl">📝</span>
            <h2 className="text-lg font-bold text-slate-100">Editor de Guion</h2>
            <span className="text-xs text-slate-500">EP #{episode.id}</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors text-2xl leading-none"
            aria-label="Cerrar editor"
          >
            ×
          </button>
        </div>

        {/* Title field */}
        <div className="px-5 pt-4 shrink-0">
          <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">
            Título del episodio
          </label>
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            placeholder="Título del episodio..."
          />
        </div>

        {/* Description field */}
        <div className="px-5 pt-3 shrink-0">
          <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">
            Descripción
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            placeholder="Descripción del episodio (opcional)..."
          />
        </div>

        {/* Script editor */}
        <div className="flex-1 min-h-0 px-5 pt-3 pb-1 flex flex-col">
          <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">
            Guion / Texto narrado
          </label>
          <ScriptTextarea
            ref={editorRef}
            value={text}
            onChange={setText}
            targetMinutes={12}
            placeholder="Escribe o pega el guion aquí. Usa la botonera para insertar etiquetas de emoción, prosodia y sfx…"
          />
        </div>

        {/* Error / success */}
        {error && (
          <div className="mx-5 mb-3 p-2 bg-red-500/10 border border-red-500/40 rounded-lg text-red-300 text-sm shrink-0">
            {error}
          </div>
        )}
        {saved && (
          <div className="mx-5 mb-3 p-2 bg-green-500/10 border border-green-500/40 rounded-lg text-green-300 text-sm shrink-0">
            ✓ Guion guardado correctamente
          </div>
        )}

        {/* Action buttons */}
        <div className="flex justify-end gap-3 px-5 py-4 border-t border-slate-700 shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200 transition-colors"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 text-sm bg-slate-700 hover:bg-slate-600 text-slate-100 rounded-lg transition-colors disabled:opacity-50"
          >
            {saving ? 'Guardando...' : '💾 Guardar'}
          </button>
          <button
            type="button"
            onClick={handleSaveAndRetry}
            disabled={saving}
            className="px-4 py-2 text-sm bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors disabled:opacity-50 font-medium"
          >
            {saving ? 'Procesando...' : '🚀 Guardar y generar audio'}
          </button>
        </div>
      </div>
    </div>
  )
}
