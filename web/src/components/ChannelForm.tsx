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
      autopilot: initial?.autopilot ?? false,
      episodes_per_week: initial?.episodes_per_week ?? 2,
      target_minutes: initial?.target_minutes ?? 10,
    })
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
    <form onSubmit={handleSubmit} className="bg-white p-6 rounded shadow space-y-4">
      <div className="bg-purple-50 border border-purple-200 rounded p-4 space-y-2">
        <label htmlFor="channel-ai-hint" className="block text-sm font-medium">
          Rellenar con IA
        </label>
        <div className="flex gap-2">
          <input
            id="channel-ai-hint"
            className="flex-1 border rounded p-2"
            placeholder="Tema del canal (opcional, p. ej. historia antigua)"
            value={hint}
            onChange={(e) => setHint(e.target.value)}
          />
          <button
            type="button"
            onClick={handleAiFill}
            disabled={aiLoading}
            className="bg-purple-600 text-white px-4 py-2 rounded disabled:opacity-50 whitespace-nowrap"
          >
            {aiLoading ? 'Generando...' : '✨ Rellenar con IA'}
          </button>
        </div>
        {aiError && <p className="text-sm text-red-600">{aiError}</p>}
      </div>
      <div>
        <label htmlFor="channel-name" className="block text-sm font-medium">Nombre</label>
        <input
          id="channel-name"
          className="w-full border rounded p-2"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
      </div>
      <div>
        <label htmlFor="channel-description" className="block text-sm font-medium">Descripción</label>
        <textarea
          id="channel-description"
          className="w-full border rounded p-2"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="channel-niche" className="block text-sm font-medium">Nicho</label>
        <input
          id="channel-niche"
          className="w-full border rounded p-2"
          value={niche}
          onChange={(e) => setNiche(e.target.value)}
        />
      </div>
      <div>
        <label htmlFor="channel-format" className="block text-sm font-medium">Formato</label>
        <select
          id="channel-format"
          className="w-full border rounded p-2"
          value={format}
          onChange={(e) => setFormat(e.target.value as ChannelFormat)}
        >
          {FORMATS.map((f) => (
            <option key={f.value} value={f.value}>{f.label}</option>
          ))}
        </select>
      </div>
      <div>
        <label htmlFor="channel-voice" className="block text-sm font-medium">Voz por defecto</label>
        <select
          id="channel-voice"
          className="w-full border rounded p-2"
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
      <div className="space-x-2">
        <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded">
          Guardar
        </button>
        <button type="button" onClick={onCancel} className="bg-gray-300 px-4 py-2 rounded">
          Cancelar
        </button>
      </div>
    </form>
  )
}
