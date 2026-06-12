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
    try {
      const result = await api.previewTts(text, selectedVoice)
      setAudioUrl(result.audio_url)
    } catch (error) {
      setPreviewError('Error generando preview: ' + String(error))
    } finally {
      setPreviewLoading(false)
    }
  }

  if (loading) return <div>Cargando voces...</div>

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold mb-4">Probar voces</h2>
      {error && <div className="bg-red-100 text-red-800 p-3 rounded mb-4">{error}</div>}
      <div className="bg-white p-6 rounded shadow">
        <label htmlFor="voice-select" className="block mb-2 font-medium">Voz</label>
        <select
          id="voice-select"
          value={selectedVoice}
          onChange={(e) => setSelectedVoice(e.target.value)}
          className="w-full p-2 border rounded mb-4"
        >
          {voices.map((voice) => (
            <option key={voice.id} value={voice.id}>
              {voice.name} ({voice.engine})
            </option>
          ))}
        </select>

        <label htmlFor="voice-text" className="block mb-2 font-medium">Texto</label>
        <textarea
          id="voice-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          className="w-full p-2 border rounded mb-4"
        />

        {previewError && <div className="bg-red-100 text-red-800 p-3 rounded mb-4">{previewError}</div>}

        <button
          onClick={handlePreview}
          disabled={previewLoading || !selectedVoice}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {previewLoading ? 'Generando...' : 'Escuchar'}
        </button>

        {audioUrl && <AudioPlayer src={audioUrl} />}
      </div>
    </div>
  )
}
