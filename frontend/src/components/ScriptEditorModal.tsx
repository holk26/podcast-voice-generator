import { useState, useEffect, useRef } from 'react'
import { Episode } from '../types'
import { useEpisodeStore } from '../stores/episodeStore'

interface Props {
  episode: Episode
  onClose: () => void
}

export default function ScriptEditorModal({ episode, onClose }: Props) {
  const updateEpisode = useEpisodeStore((s) => s.updateEpisode)
  const retryEpisode = useEpisodeStore((s) => s.retryEpisode)
  const [text, setText] = useState(episode.source_text || '')
  const [title, setTitle] = useState(episode.title)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Word / char count
  const charCount = text.length
  const wordCount = text.trim() ? text.trim().split(/\s+/).length : 0
  const estimatedMinutes = Math.round(wordCount / 140) // ~140 wpm Spanish narration

  useEffect(() => {
    textareaRef.current?.focus()
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
      await updateEpisode(episode.id, { title, source_text: text })
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
      await updateEpisode(episode.id, { title, source_text: text })
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

        {/* Script textarea */}
        <div className="flex-1 min-h-0 px-5 pt-3 pb-1 flex flex-col">
          <label className="block text-xs font-medium text-slate-400 mb-1 uppercase tracking-wider">
            Guion / Texto narrado
          </label>
          <textarea
            ref={textareaRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="flex-1 min-h-0 w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-slate-100 text-sm font-mono leading-relaxed resize-none focus:outline-none focus:ring-2 focus:ring-purple-500"
            placeholder="Escribe o pega el guion aquí. Puedes usar etiquetas de emoción como <|emotion:contemplation|>, <|prosody:pause|>, <|sfx:sigh|>..."
            spellCheck={false}
          />
        </div>

        {/* Stats bar */}
        <div className="px-5 py-2 flex gap-4 text-xs text-slate-500 shrink-0">
          <span>{charCount.toLocaleString()} caracteres</span>
          <span>{wordCount.toLocaleString()} palabras</span>
          <span className={`font-medium ${estimatedMinutes >= 10 ? 'text-green-400' : 'text-amber-400'}`}>
            ~{estimatedMinutes} min estimados (objetivo: 12 min)
          </span>
        </div>

        {/* Emotion tag reference */}
        <div className="mx-5 mb-3 p-3 bg-slate-800/60 border border-slate-700/50 rounded-lg shrink-0">
          <p className="text-xs text-slate-400 font-medium mb-1.5">Etiquetas disponibles:</p>
          <div className="flex flex-wrap gap-1.5">
            {[
              '<|emotion:contemplation|>',
              '<|emotion:sadness|>',
              '<|emotion:determination|>',
              '<|emotion:bitterness|>',
              '<|emotion:fear|>',
              '<|emotion:helplessness|>',
              '<|emotion:affection|>',
              '<|prosody:pause|>',
              '<|sfx:sigh|>',
              '<|sfx:laughter|>',
            ].map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => {
                  const el = textareaRef.current
                  if (!el) return
                  const start = el.selectionStart
                  const end = el.selectionEnd
                  const newText = text.slice(0, start) + tag + ' ' + text.slice(end)
                  setText(newText)
                  setTimeout(() => {
                    el.focus()
                    el.setSelectionRange(start + tag.length + 1, start + tag.length + 1)
                  }, 0)
                }}
                className="text-xs px-2 py-0.5 bg-purple-900/40 border border-purple-700/50 text-purple-300 rounded hover:bg-purple-800/60 transition-colors font-mono"
              >
                {tag.replace('<|', '').replace('|>', '')}
              </button>
            ))}
          </div>
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
