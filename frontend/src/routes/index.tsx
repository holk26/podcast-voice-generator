import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect, useMemo } from 'react'
import { useEpisodeStore } from '../stores/episodeStore'
import { useVoiceStore } from '../stores/voiceStore'
import { useChannelStore } from '../stores/channelStore'
import { Episode } from '../types'

export const Route = createFileRoute('/')({
  component: DashboardPage,
})

function DashboardPage() {
  const episodes = useEpisodeStore((state) => state.episodes)
  const episodesLoading = useEpisodeStore((state) => state.loading)
  const episodesError = useEpisodeStore((state) => state.error)
  const fetchEpisodes = useEpisodeStore((state) => state.fetchEpisodes)
  const voices = useVoiceStore((state) => state.voices)
  const voicesLoading = useVoiceStore((state) => state.loading)
  const voicesError = useVoiceStore((state) => state.error)
  const fetchVoices = useVoiceStore((state) => state.fetchVoices)
  const channels = useChannelStore((state) => state.channels)
  const fetchChannels = useChannelStore((state) => state.fetchChannels)

  useEffect(() => {
    fetchEpisodes()
    fetchVoices()
    fetchChannels()
  }, [fetchEpisodes, fetchVoices, fetchChannels])

  const counts = useMemo(
    () => ({
      completed: episodes.filter((e) => e.status === 'completed').length,
      pending: episodes.filter((e) => e.status === 'pending').length,
      running: episodes.filter((e) => e.status === 'running').length,
      failed: episodes.filter((e) => e.status === 'failed').length,
    }),
    [episodes]
  )

  const loading = episodesLoading || voicesLoading
  const error = episodesError || voicesError

  const recentEpisodes = useMemo(
    () =>
      [...episodes]
        .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
        .slice(0, 5),
    [episodes],
  )
  const recentStatusBadge: Record<Episode['status'], string> = {
    pending: 'text-amber-300',
    running: 'text-purple-300',
    completed: 'text-green-300',
    failed: 'text-red-300',
  }
  const channelWithPending = channels.find(
    (c) => (c.entries_total ?? 0) > (c.entries_generated ?? 0),
  )

  if (loading) return <div className="text-slate-400">Cargando dashboard...</div>

  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight mb-6">Dashboard</h2>
      {error && (
        <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg mb-4">
          Error: {error}
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-slate-800/50 border border-slate-700 p-4 rounded-xl shadow-lg shadow-black/20">
          <p className="text-sm text-slate-400">Completados</p>
          <p className="text-2xl font-bold text-green-400">{counts.completed}</p>
        </div>
        <div className="bg-slate-800/50 border border-slate-700 p-4 rounded-xl shadow-lg shadow-black/20">
          <p className="text-sm text-slate-400">Pendientes</p>
          <p className="text-2xl font-bold text-amber-400">{counts.pending}</p>
        </div>
        <div className="bg-slate-800/50 border border-slate-700 p-4 rounded-xl shadow-lg shadow-black/20">
          <p className="text-sm text-slate-400">En progreso</p>
          <p className="text-2xl font-bold text-purple-400">{counts.running}</p>
        </div>
        <div className="bg-slate-800/50 border border-slate-700 p-4 rounded-xl shadow-lg shadow-black/20">
          <p className="text-sm text-slate-400">Fallidos</p>
          <p className="text-2xl font-bold text-red-400">{counts.failed}</p>
        </div>
      </div>

      <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl shadow-lg shadow-black/20 mb-6">
        <h3 className="text-lg font-bold tracking-tight mb-4">Acciones rápidas</h3>
        <div className="space-x-4">
          <Link to="/create" className="inline-block bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors">
            Nuevo episodio
          </Link>
          <Link to="/voices" className="inline-block bg-slate-700 text-slate-100 px-4 py-2 rounded-lg hover:bg-slate-600 transition-colors">
            Probar voces
          </Link>
          <Link to="/queue" className="inline-block bg-slate-700 text-slate-100 px-4 py-2 rounded-lg hover:bg-slate-600 transition-colors">
            Ver cola
          </Link>
        </div>
      </div>

      <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl shadow-lg shadow-black/20 mb-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold tracking-tight">Episodios recientes</h3>
          <Link to="/queue" className="text-sm text-purple-400 hover:text-purple-300 transition-colors">
            Ver cola →
          </Link>
        </div>
        {recentEpisodes.length === 0 ? (
          <p className="text-sm text-slate-400">Aún no hay episodios. Crea el primero desde "Nuevo episodio".</p>
        ) : (
          <ul className="divide-y divide-slate-700/60">
            {recentEpisodes.map((ep) => (
              <li key={ep.id} className="py-2 flex justify-between items-center gap-4">
                <Link
                  to="/queue"
                  search={{ highlight: ep.id }}
                  className="font-medium text-slate-100 hover:text-purple-300 transition-colors truncate"
                >
                  {ep.title}
                </Link>
                <span className={`text-sm ${recentStatusBadge[ep.status]} shrink-0`}>
                  {ep.status}
                </span>
              </li>
            ))}
          </ul>
        )}
        {channelWithPending && (
          <p className="text-sm mt-4">
            <Link
              to="/channels/$id/plan"
              params={{ id: String(channelWithPending.id) }}
              className="text-violet-400 hover:text-violet-300 transition-colors"
            >
              → {channelWithPending.name} tiene {(channelWithPending.entries_total ?? 0) - (channelWithPending.entries_generated ?? 0)} entradas pendientes de generar
            </Link>
          </p>
        )}
      </div>

      <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl shadow-lg shadow-black/20">
        <h3 className="text-lg font-bold tracking-tight mb-4">Voces disponibles ({voices.length})</h3>
        <ul className="divide-y divide-slate-700/60">
          {voices.map((voice) => (
            <li key={voice.id} className="py-2 flex justify-between">
              <span className="font-medium text-slate-100">{voice.name}</span>
              <span className="text-sm text-slate-400">{voice.language} • {voice.gender}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
