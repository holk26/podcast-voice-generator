import { useState } from 'react'
import { Episode } from '../types'
import AudioPlayer from './AudioPlayer'
import ScriptEditorModal from './ScriptEditorModal'
import { useEpisodeStore } from '../stores/episodeStore'
import { useAppStore } from '../stores/appStore'

interface Props {
  episode: Episode
  onDelete: (id: number) => void
  onRetry: (id: number) => void
  highlighted?: boolean
}

const statusLabels: Record<Episode['status'], string> = {
  pending: 'Pendiente',
  running: 'En progreso',
  completed: 'Completado',
  failed: 'Fallido',
}

const statusColors: Record<Episode['status'], string> = {
  pending: 'bg-amber-500/15 border border-amber-500/40 text-amber-300',
  running: 'bg-purple-500/15 border border-purple-500/40 text-purple-300 animate-pulse',
  completed: 'bg-green-500/15 border border-green-500/40 text-green-300',
  failed: 'bg-red-500/15 border border-red-500/40 text-red-300',
}

export default function EpisodeCard({ episode, onDelete, onRetry, highlighted }: Props) {
  const publishEpisode = useEpisodeStore((s) => s.publishEpisode)
  const unpublishEpisode = useEpisodeStore((s) => s.unpublishEpisode)
  const askConfirm = useAppStore((s) => s.askConfirm)
  const [editing, setEditing] = useState(false)
  const published = Boolean(episode.published_at)

  const handleDelete = async () => {
    const ok = await askConfirm({
      title: 'Eliminar episodio',
      message: `¿Seguro que quieres eliminar "${episode.title}"? Esta acción no se puede deshacer.`,
      confirmLabel: 'Eliminar',
      danger: true,
    })
    if (ok) onDelete(episode.id)
  }

  return (
    <div className={`bg-slate-800/50 border border-slate-700 p-4 rounded-xl shadow-lg shadow-black/20 ${highlighted ? 'ring-2 ring-purple-500' : ''}`}>
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-bold text-lg tracking-tight text-slate-100">{episode.title}</h3>
          <p className="text-sm text-slate-400">{episode.type} • {episode.voice_id}</p>
          {episode.description && (
            <p className="text-sm text-slate-300 mt-1 whitespace-pre-wrap">{episode.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          {published && (
            <span className="px-2 py-1 rounded-lg text-xs font-medium bg-emerald-500/15 border border-emerald-500/40 text-emerald-300">
              Publicado · {new Date(episode.published_at!).toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })}
            </span>
          )}
          <span className={`px-2 py-1 rounded-lg text-xs font-medium ${statusColors[episode.status] || 'bg-slate-700 text-slate-300'}`}>
            {statusLabels[episode.status]}
          </span>
        </div>
      </div>

      {episode.error_message && (
        <p className="text-red-400 text-sm mt-2">{episode.error_message}</p>
      )}

      {episode.audio_url && (
        <AudioPlayer src={episode.audio_url} />
      )}

      <div className="mt-3 flex gap-4">
        {(episode.status === 'failed' || episode.status === 'running') && (
          <button
            type="button"
            onClick={() => onRetry(episode.id)}
            aria-label={`Reintentar episodio ${episode.title}`}
            className="text-blue-400 text-sm hover:text-blue-300 hover:underline transition-colors"
          >
            {episode.status === 'running' ? 'Reintentar (atascado)' : 'Reintentar'}
          </button>
        )}
        {episode.status === 'completed' && !published && (
          <button
            type="button"
            onClick={() => publishEpisode(episode.id)}
            className="text-emerald-400 text-sm hover:text-emerald-300 hover:underline transition-colors"
          >
            Marcar publicado
          </button>
        )}
        {published && (
          <button
            type="button"
            onClick={() => unpublishEpisode(episode.id)}
            className="text-slate-400 text-sm hover:text-slate-300 hover:underline transition-colors"
          >
            Desmarcar publicado
          </button>
        )}
        <button
          type="button"
          onClick={() => setEditing(true)}
          className="text-amber-400 text-sm hover:text-amber-300 hover:underline transition-colors"
        >
          Editar guion
        </button>
        <button
          type="button"
          onClick={handleDelete}
          aria-label={`Eliminar episodio ${episode.title}`}
          className="text-red-400 text-sm hover:text-red-300 hover:underline transition-colors"
        >
          Eliminar
        </button>
      </div>
      {editing && (
        <ScriptEditorModal episode={episode} onClose={() => setEditing(false)} />
      )}
    </div>
  )
}
