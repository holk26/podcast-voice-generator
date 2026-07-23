import { useState } from 'react'
import { ChannelFormat, CreateChannelRequest, Voice } from '../types'

interface Props {
  voices: Voice[]
  onSubmit: (data: CreateChannelRequest) => void
  onCancel: () => void
}

const FORMATS: { value: ChannelFormat; label: string }[] = [
  { value: 'podcast', label: 'Podcast' },
  { value: 'news', label: 'Noticias' },
  { value: 'meditation', label: 'Meditación' },
  { value: 'motivation', label: 'Motivación' },
]

export default function ChannelForm({ voices, onSubmit, onCancel }: Props) {
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [niche, setNiche] = useState('')
  const [format, setFormat] = useState<ChannelFormat>('podcast')
  const [voiceId, setVoiceId] = useState(voices[0]?.id ?? 'jorge')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({ name, description, niche, format, default_voice_id: voiceId, is_active: true })
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white p-6 rounded shadow space-y-4">
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
