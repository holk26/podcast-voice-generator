import { useEffect, useState } from 'react'
import { useEpisodeStore } from '../../stores/episodeStore'
import EpisodeCard from '../EpisodeCard'
import { Channel } from '../../types'

export default function EpisodesTab({ channel }: { channel: Channel }) {
  const {
    episodes, loading, error,
    fetchEpisodes, deleteEpisode, retryEpisode,
  } = useEpisodeStore()
  const [filter, setFilter] = useState<'all' | 'unpublished' | 'published'>('all')

  useEffect(() => {
    fetchEpisodes(channel.id)
  }, [channel.id, fetchEpisodes])

  const channelEpisodes = episodes.filter((e) => e.channel_id === channel.id)
  const visible = channelEpisodes.filter((e) => {
    if (filter === 'unpublished') return !e.published_at
    if (filter === 'published') return !!e.published_at
    return true
  })

  return (
    <div>
      <div className="flex gap-2 mb-4">
        {([['all', 'Todos'], ['unpublished', 'Sin publicar'], ['published', 'Publicados']] as const).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setFilter(key)}
            className={`px-3 py-1 rounded-lg text-sm border ${
              filter === key
                ? 'bg-purple-600 border-purple-500 text-white'
                : 'bg-slate-800 border-slate-600 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>
      {error && (
        <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg mb-4">Error: {error}</div>
      )}
      {loading && <div className="text-slate-400">Cargando episodios...</div>}
      {!loading && visible.length === 0 && (
        <p className="text-slate-400">No hay episodios{filter !== 'all' ? ' con este filtro' : ''} en este canal. Usa «Cargar guion» o «Generar guion con IA».</p>
      )}
      <div className="space-y-3">
        {visible.map((episode) => (
          <EpisodeCard
            key={episode.id}
            episode={episode}
            onDelete={deleteEpisode}
            onRetry={retryEpisode}
          />
        ))}
      </div>
    </div>
  )
}
