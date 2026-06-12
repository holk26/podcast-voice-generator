import { Episode } from '../types'
import AudioPlayer from './AudioPlayer'

interface Props {
  episode: Episode
  onDelete: (id: number) => void
  highlighted?: boolean
}

export default function EpisodeCard({ episode, onDelete, highlighted }: Props) {
  const statusColors: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800',
    running: 'bg-blue-100 text-blue-800',
    completed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  }

  return (
    <div className={`bg-white p-4 rounded shadow ${highlighted ? 'ring-2 ring-blue-500' : ''}`}>
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-bold text-lg">{episode.title}</h3>
          <p className="text-sm text-gray-600">{episode.type} • {episode.voice_id}</p>
        </div>
        <span className={`px-2 py-1 rounded text-xs font-medium ${statusColors[episode.status] || 'bg-gray-100'}`}>
          {episode.status}
        </span>
      </div>

      {episode.error_message && (
        <p className="text-red-600 text-sm mt-2">{episode.error_message}</p>
      )}

      {episode.audio_url && (
        <AudioPlayer src={episode.audio_url} />
      )}

      <button
        onClick={() => onDelete(episode.id)}
        className="mt-3 text-red-600 text-sm hover:underline"
      >
        Eliminar
      </button>
    </div>
  )
}
