import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import CreateEpisodeForm from '../components/CreateEpisodeForm'
import { useEpisodeStore } from '../stores/episodeStore'
import { useVoiceStore } from '../stores/voiceStore'
import { useAppStore } from '../stores/appStore'
import { CreateEpisodeRequest } from '../types'

export const Route = createFileRoute('/create')({
  component: CreatePage,
})

function CreatePage() {
  const navigate = useNavigate()
  const { createEpisode } = useEpisodeStore()
  const fetchVoices = useVoiceStore((state) => state.fetchVoices)
  const pushToast = useAppStore((s) => s.pushToast)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchVoices()
  }, [fetchVoices])

  const handleSubmit = async (data: CreateEpisodeRequest) => {
    setLoading(true)
    try {
      const episode = await createEpisode(data)
      navigate({ to: '/queue', search: { highlight: episode.id } })
    } catch (error) {
      pushToast('Error creando episodio: ' + String(error), 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold tracking-tight mb-4">Crear episodio</h2>
      <CreateEpisodeForm onSubmit={handleSubmit} loading={loading} />
    </div>
  )
}
