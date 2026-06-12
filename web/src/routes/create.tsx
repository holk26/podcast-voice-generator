import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useState } from 'react'
import CreateEpisodeForm from '../components/CreateEpisodeForm'
import { useEpisodeStore } from '../stores/episodeStore'
import { CreateEpisodeRequest } from '../types'

export const Route = createFileRoute('/create')({
  component: CreatePage,
})

function CreatePage() {
  const navigate = useNavigate()
  const { createEpisode } = useEpisodeStore()
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (data: CreateEpisodeRequest) => {
    setLoading(true)
    try {
      const episode = await createEpisode(data)
      navigate({ to: '/queue', search: { highlight: episode.id } })
    } catch (error) {
      alert('Error creando episodio: ' + String(error))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-2xl">
      <h2 className="text-2xl font-bold mb-4">Crear episodio</h2>
      <CreateEpisodeForm onSubmit={handleSubmit} loading={loading} />
    </div>
  )
}
