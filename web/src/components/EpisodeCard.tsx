import { Episode } from '../types'
import AudioPlayer from './AudioPlayer'

interface Props {
  episode: Episode
  onDelete: (id: number) => void
  highlighted?: boolean
}

const statusColors: Record<Episode['status'], string> = {
  pending: 'bg-amber-500/15 border border-amber-500/40 text-amber-300',
  running: 'bg-purple-500/15 border border-purple-500/40 text-purple-300 animate-pulse',
  completed: 'bg-green-500/15 border border-green-500/40 text-green-300',
  failed: 'bg-red-500/15 border border-red-500/40 text-red-300',
}

export default function EpisodeCard({ episode, onDelete, highlighted }: Props) {
  return (
    <div className={`bg-slate-800/50 border border-slate-700 p-4 rounded-xl shadow-lg shadow-black/20 ${highlighted ? 'ring-2 ring-purple-500' : ''}`}>
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-bold text-lg tracking-tight text-slate-100">{episode.title}</h3>
          <p className="text-sm text-slate-400">{episode.type} • {episode.voice_id}</p>
        </div>
        <span className={`px-2 py-1 rounded-lg text-xs font-medium ${statusColors[episode.status] || 'bg-slate-700 text-slate-300'}`}>
          {episode.status}
        </span>
      </div>

      {episode.error_message && (
        <p className="text-red-400 text-sm mt-2">{episode.error_message}</p>
      )}

      {episode.audio_url && (
        <AudioPlayer src={episode.audio_url} />
      )}

      <button
        type="button"
        onClick={() => onDelete(episode.id)}
        aria-label={`Eliminar episodio ${episode.title}`}
        className="mt-3 text-red-400 text-sm hover:text-red-300 hover:underline transition-colors"
      >
        Eliminar
      </button>
    </div>
  )
}
