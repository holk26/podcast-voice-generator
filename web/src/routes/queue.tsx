import { createFileRoute, useSearch } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useEpisodeStore } from '../stores/episodeStore'
import EpisodeCard from '../components/EpisodeCard'

export const Route = createFileRoute('/queue')({
  component: QueuePage,
})

function QueuePage() {
  const search = useSearch({ from: '/queue' }) as { highlight?: number }
  const { episodes, loading, fetchEpisodes, deleteEpisode, updateEpisode } = useEpisodeStore()

  useEffect(() => {
    fetchEpisodes()
  }, [fetchEpisodes])

  useEffect(() => {
    episodes.forEach((episode) => {
      if (episode.status === 'pending' || episode.status === 'running') {
        const eventSource = new EventSource(`/api/episodes/${episode.id}/events`)
        eventSource.onmessage = (event) => {
          const data = JSON.parse(event.data)
          updateEpisode({ ...episode, ...data })
        }
        eventSource.onerror = () => {
          eventSource.close()
        }
        return () => eventSource.close()
      }
    })
  }, [episodes, updateEpisode])

  if (loading) return <div>Cargando episodios...</div>

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Cola de episodios</h2>
      <div className="space-y-4">
        {episodes.map((episode) => (
          <EpisodeCard
            key={episode.id}
            episode={episode}
            onDelete={deleteEpisode}
            highlighted={search.highlight === episode.id}
          />
        ))}
      </div>
    </div>
  )
}
