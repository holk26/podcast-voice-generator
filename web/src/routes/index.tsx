import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect, useMemo } from 'react'
import { useEpisodeStore } from '../stores/episodeStore'
import { useVoiceStore } from '../stores/voiceStore'

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

  useEffect(() => {
    fetchEpisodes()
    fetchVoices()
  }, [fetchEpisodes, fetchVoices])

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

  if (loading) return <div>Cargando dashboard...</div>

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Dashboard</h2>
      {error && (
        <div className="bg-red-100 text-red-800 p-3 rounded mb-4">
          Error: {error}
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <div className="bg-white p-4 rounded shadow">
          <p className="text-sm text-gray-600">Completados</p>
          <p className="text-2xl font-bold text-green-600">{counts.completed}</p>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <p className="text-sm text-gray-600">Pendientes</p>
          <p className="text-2xl font-bold text-yellow-600">{counts.pending}</p>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <p className="text-sm text-gray-600">En progreso</p>
          <p className="text-2xl font-bold text-blue-600">{counts.running}</p>
        </div>
        <div className="bg-white p-4 rounded shadow">
          <p className="text-sm text-gray-600">Fallidos</p>
          <p className="text-2xl font-bold text-red-600">{counts.failed}</p>
        </div>
      </div>

      <div className="bg-white p-6 rounded shadow mb-6">
        <h3 className="text-lg font-bold mb-4">Acciones rápidas</h3>
        <div className="space-x-4">
          <Link to="/create" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            Nuevo episodio
          </Link>
          <Link to="/voices" className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700">
            Probar voces
          </Link>
          <Link to="/queue" className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700">
            Ver cola
          </Link>
        </div>
      </div>

      <div className="bg-white p-6 rounded shadow">
        <h3 className="text-lg font-bold mb-4">Voces disponibles ({voices.length})</h3>
        <ul className="divide-y">
          {voices.map((voice) => (
            <li key={voice.id} className="py-2 flex justify-between">
              <span className="font-medium">{voice.name}</span>
              <span className="text-sm text-gray-500">{voice.language} • {voice.gender}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
