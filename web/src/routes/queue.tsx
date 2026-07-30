import { createFileRoute, useSearch } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useEpisodeStore } from '../stores/episodeStore'
import { useEpisodeSSE } from '../hooks/useEpisodeSSE'
import EpisodeCard from '../components/EpisodeCard'
import LiveJobsPanel from '../components/LiveJobsPanel'

export const Route = createFileRoute('/queue')({
  component: QueuePage,
})

function QueuePage() {
  const search = useSearch({ from: '/queue' }) as { highlight?: number }
  const episodes = useEpisodeStore((state) => state.episodes)
  const loading = useEpisodeStore((state) => state.loading)
  const error = useEpisodeStore((state) => state.error)
  const fetchEpisodes = useEpisodeStore((state) => state.fetchEpisodes)
  const deleteEpisode = useEpisodeStore((state) => state.deleteEpisode)
  const retryEpisode = useEpisodeStore((state) => state.retryEpisode)
  const applyEpisodeUpdate = useEpisodeStore((state) => state.applyEpisodeUpdate)

  useEffect(() => {
    fetchEpisodes()
  }, [fetchEpisodes])

  useEpisodeSSE(episodes, applyEpisodeUpdate)

  if (loading) return <div className="text-slate-400">Cargando episodios...</div>

  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight mb-4">Cola de episodios</h2>
      <LiveJobsPanel />
      {error && (
        <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg mb-4">
          Error: {error}
        </div>
      )}
      <div className="space-y-4">
        {episodes.map((episode) => (
          <EpisodeCard
            key={episode.id}
            episode={episode}
            onDelete={deleteEpisode}
            onRetry={retryEpisode}
            highlighted={Number(search.highlight) === episode.id}
          />
        ))}
      </div>
    </div>
  )
}
