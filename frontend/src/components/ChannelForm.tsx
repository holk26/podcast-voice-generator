import { useState } from 'react'
import { Channel, ChannelFormat, CreateChannelRequest, Voice } from '../types'
import { api } from '../api/client'

interface Props {
  voices: Voice[]
  initial?: Channel
  onSubmit: (data: CreateChannelRequest) => void
  onCancel: () => void
}

const FORMATS: { value: ChannelFormat; label: string }[] = [
  { value: 'podcast', label: 'Podcast' },
  { value: 'news', label: 'Noticias' },
  { value: 'meditation', label: 'Meditación' },
  { value: 'motivation', label: 'Motivación' },
]

export default function ChannelForm({ voices, initial, onSubmit, onCancel }: Props) {
  const [name, setName] = useState(initial?.name ?? '')
  const [description, setDescription] = useState(initial?.description ?? '')
  const [niche, setNiche] = useState(initial?.niche ?? '')
  const [format, setFormat] = useState<ChannelFormat>(initial?.format ?? 'podcast')
  const [voiceId, setVoiceId] = useState(initial?.default_voice_id ?? voices[0]?.id ?? 'jorge')
  const [brief, setBrief] = useState(initial?.brief ?? '')
  const [hint, setHint] = useState('')
  const [aiLoading, setAiLoading] = useState(false)
  const [aiError, setAiError] = useState<string | null>(null)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      name,
      description,
      niche,
      format,
      default_voice_id: voiceId,
      is_active: initial?.is_active ?? true,
      brief: brief || undefined,
      autopilot: initial?.autopilot ?? false,
      episodes_per_week: initial?.episodes_per_week ?? 2,
      target_minutes: initial?.target_minutes ?? 10,
    })
  }

  const handleImprovePrompt = async () => {
    if (!initial) return
    setAiLoading(true)
    setAiError(null)
    try {
      const { brief: newBrief } = await api.improveChannelPrompt(initial.id)
      setBrief(newBrief)
    } catch (err) {
      setAiError(String(err))
    } finally {
      setAiLoading(false)
    }
  }

  const handleAiFill = async () => {
    setAiLoading(true)
    setAiError(null)
    try {
      const s = await api.suggestChannel(hint || undefined)
      setName(s.name)
      setDescription(s.description)
      setNiche(s.niche)
      setFormat(s.format)
    } catch (err) {
      setAiError(String(err))
    } finally {
      setAiLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl shadow-lg shadow-black/20 space-y-4">
      <div className="bg-purple-500/10 border border-purple-500/40 rounded-xl p-4 space-y-2">
        <label htmlFor="channel-ai-hint" className="block text-sm font-medium text-purple-200">
          Rellenar con IA
        </label>
        <div className="flex gap-2">
          <input
            id="channel-ai-hint"
            className="flex-1 bg-slate-800 border border-slate-600 text-slate-100 placeholder-slate-500 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
            placeholder="Tema del canal (opcional, p. ej. historia antigua)"
            value={hint}
            onChange={(e) => setHint(e.target.value)}
          />
          <button
            type="button"
            onClick={handleAiFill}
            disabled={aiLoading}
            className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {aiLoading ? 'Generando...' : '✨ Rellenar con IA'}
          </button>
        </div>
        {aiError && <p className="text-sm text-red-400">{aiError}</p>}
      </div>
      <div>
        <label htmlFor="channel-name" className="block text-sm font-medium text-slate-200">Nombre</label>
        <input
          id="channel-name"
          className="w-full bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>
      <div>
        <label htmlFor="channel-description" className="block text-sm font-medium text-slate-200">Descripción</label>
        <textarea
          id="channel-description"
          className="w-full bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="channel-niche" className="block text-sm font-medium text-slate-200">Nicho</label>
        <input
          id="channel-niche"
          className="w-full bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
          value={niche}
          onChange={(e) => setNiche(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="channel-format" className="block text-sm font-medium text-slate-200">Formato</label>
        <select
          id="channel-format"
          className="w-full bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
          value={format}
          onChange={(e) => setFormat(e.target.value as ChannelFormat)}
        >
          {FORMATS.map((f) => (
            <option key={f.value} value={f.value}>{f.label}</option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="channel-voice" className="block text-sm font-medium text-slate-200">Voz por defecto</label>
        <select
          id="channel-voice"
          className="w-full bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
          value={voiceId}
          onChange={(e) => setVoiceId(e.target.value)}
          required
        >
          {voices.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name} ({v.engine})
            </option>
          ))}
        </select>
      </div>
      <div>
        <div className="flex justify-between items-center mb-1">
          <label htmlFor="channel-brief" className="block text-sm font-medium text-slate-200">
            Brief de producción (lo siguen los agentes al generar)
          </label>
          {initial && (
            <button
              type="button"
              onClick={handleImprovePrompt}
              disabled={aiLoading}
              className="text-sm bg-violet-600 text-white px-3 py-1 rounded-lg hover:bg-violet-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {aiLoading ? 'Mejorando...' : '🪄 Mejorar con IA'}
            </button>
          )}
        </div>
        <textarea
          id="channel-brief"
          className="w-full bg-slate-800 border border-slate-600 text-slate-100 placeholder-slate-500 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
          rows={5}
          placeholder="Idioma del contenido, audiencia, tono, estructura y reglas del canal. Vacío = comportamiento por defecto (español)."
          value={brief}
          onChange={(e) => setBrief(e.target.value)}
        />
      </div>
      <div className="space-x-2">
        <button type="submit" className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors">
          Guardar
        </button>
        <button type="button" onClick={onCancel} className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg hover:bg-slate-600 transition-colors">
          Cancelar
        </button>
      </div>
    </form>
  )
}
