import { useState } from 'react'
import { useVoiceStore } from '../stores/voiceStore'
import { CreateEpisodeRequest } from '../types'

interface Props {
  onSubmit: (data: CreateEpisodeRequest) => void
  loading: boolean
}

export default function CreateEpisodeForm({ onSubmit, loading }: Props) {
  const { voices } = useVoiceStore()
  const [title, setTitle] = useState('')
  const [type, setType] = useState('podcast')
  const [sourceText, setSourceText] = useState('')
  const [voiceId, setVoiceId] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({ title, type, source_text: sourceText, voice_id: voiceId })
  }

  return (
    <form onSubmit={handleSubmit} className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl shadow-lg shadow-black/20 space-y-4">
      <div>
        <label className="block font-medium text-slate-200 mb-1">Título</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
          className="w-full p-2 bg-slate-800 border border-slate-600 text-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
      </div>

      <div>
        <label className="block font-medium text-slate-200 mb-1">Tipo</label>
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="w-full p-2 bg-slate-800 border border-slate-600 text-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="podcast">Podcast</option>
          <option value="motivation">Motivación</option>
          <option value="meditation">Meditación</option>
          <option value="audiobook">Audiolibro</option>
        </select>
      </div>

      <div>
        <label className="block font-medium text-slate-200 mb-1">Voz</label>
        <select
          value={voiceId}
          onChange={(e) => setVoiceId(e.target.value)}
          required
          className="w-full p-2 bg-slate-800 border border-slate-600 text-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          <option value="">Seleccionar voz</option>
          {voices.map((voice) => (
            <option key={voice.id} value={voice.id}>
              {voice.name}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="block font-medium text-slate-200 mb-1">Texto / Guion</label>
        <textarea
          value={sourceText}
          onChange={(e) => setSourceText(e.target.value)}
          rows={8}
          required
          className="w-full p-2 bg-slate-800 border border-slate-600 text-slate-100 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? 'Creando...' : 'Generar episodio'}
      </button>
    </form>
  )
}
