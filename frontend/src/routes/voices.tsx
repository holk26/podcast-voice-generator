import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useVoiceStore } from '../stores/voiceStore'
import { api } from '../api/client'
import AudioPlayer from '../components/AudioPlayer'

export const Route = createFileRoute('/voices')({
  component: VoicesPage,
})

function VoicesPage() {
  const { voices, loading, error, fetchVoices } = useVoiceStore()
  const [selectedVoice, setSelectedVoice] = useState('')
  const [text, setText] = useState('Hola, esta es una prueba de voz.')
  const [audioUrl, setAudioUrl] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)

  useEffect(() => {
    fetchVoices()
  }, [fetchVoices])

  useEffect(() => {
    if (voices.length > 0 && !selectedVoice) {
      setSelectedVoice(voices[0].id)
    }
  }, [voices, selectedVoice])

  const handlePreview = async () => {
    setPreviewLoading(true)
    setPreviewError(null)
    setAudioUrl(null) // evita que el audio anterior siga sonando mientras carga el nuevo
    try {
      const result = await api.previewTts(text, selectedVoice)
      setAudioUrl(result.audio_url)
    } catch (error) {
      setPreviewError('Error generando preview: ' + String(error))
    } finally {
      setPreviewLoading(false)
    }
  }

  if (loading) return <div className="text-slate-400">Cargando voces...</div>

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold tracking-tight mb-4">Probar voces</h2>
      {error && <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg mb-4">{error}</div>}
      <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl shadow-lg shadow-black/20">
        <label htmlFor="voice-select" className="block mb-2 font-medium text-slate-200">Voz</label>
        <select
          id="voice-select"
          value={selectedVoice}
          onChange={(e) => {
            setSelectedVoice(e.target.value)
            setAudioUrl(null) // limpia el audio anterior al cambiar de voz
          }}
          className="w-full p-2 bg-slate-800 border border-slate-600 text-slate-100 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-purple-500"
        >
          {voices.map((voice) => (
            <option key={voice.id} value={voice.id}>
              {voice.type === 'cloned' ? '🎙️ ' : ''}
              {voice.type === 'cloned' ? voice.name : `${voice.name} (${voice.engine})`}
              {voice.type === 'cloned' ? ' — clonada' : ''}
            </option>
          ))}
        </select>

        <label htmlFor="voice-text" className="block mb-2 font-medium text-slate-200">Texto</label>
        <textarea
          id="voice-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          className="w-full p-2 bg-slate-800 border border-slate-600 text-slate-100 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-purple-500"
        />

        {previewError && <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg mb-4">{previewError}</div>}

        <button
          onClick={handlePreview}
          disabled={previewLoading || !selectedVoice}
          className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {previewLoading ? 'Generando...' : 'Escuchar'}
        </button>

        {audioUrl && <AudioPlayer src={audioUrl} />}
      </div>
    </div>
  )
}
