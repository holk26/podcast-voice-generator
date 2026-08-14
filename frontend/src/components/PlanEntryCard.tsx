import { useState } from 'react'
import { useChannelStore } from '../stores/channelStore'
import { ContentPlanEntry } from '../types'

interface Props {
  entry: ContentPlanEntry
  onApprove: (id: number) => void
  onReject: (id: number) => void
  onDelete: (id: number) => void
}

const statusLabels: Record<string, string> = {
  draft: 'Borrador',
  generated: 'Generado',
  rejected: 'Rechazado',
}

const statusBadge: Record<string, string> = {
  draft: 'bg-amber-500/15 border border-amber-500/40 text-amber-300',
  generated: 'bg-green-500/15 border border-green-500/40 text-green-300',
  rejected: 'bg-red-500/15 border border-red-500/40 text-red-300',
}

export default function PlanEntryCard({ entry, onApprove, onReject, onDelete }: Props) {
  const updateEntry = useChannelStore((s) => s.updateEntry)
  const [editing, setEditing] = useState(false)
  const [title, setTitle] = useState(entry.title)
  const [description, setDescription] = useState(entry.description ?? '')
  const [date, setDate] = useState((entry.scheduled_date ?? '').slice(0, 10))

  const handleSave = async () => {
    await updateEntry(entry.id, {
      title,
      description,
      scheduled_date: date || undefined,
    })
    setEditing(false)
  }

  if (editing) {
    return (
      <div className="bg-slate-800/50 border border-slate-700 p-4 rounded-xl shadow-lg shadow-black/20 border-l-4 border-l-violet-500 space-y-2">
        <input
          className="w-full bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 font-bold focus:outline-none focus:ring-2 focus:ring-purple-500"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          className="w-full bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <div className="flex items-center gap-2">
          <label className="text-sm text-slate-400">Fecha:</label>
          <input
            type="date"
            className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-1 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>
        <div className="space-x-2">
          <button
            type="button"
            onClick={handleSave}
            className="bg-purple-600 text-white px-3 py-1 rounded-lg text-sm hover:bg-purple-500 transition-colors"
          >
            Guardar
          </button>
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="bg-slate-700 text-slate-100 px-3 py-1 rounded-lg text-sm hover:bg-slate-600 transition-colors"
          >
            Cancelar
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-slate-800/50 border border-slate-700 p-4 rounded-xl shadow-lg shadow-black/20 border-l-4 border-l-purple-500">
      <div className="flex justify-between items-start">
        <div className="flex-1 min-w-0">
          <h4 className="font-bold tracking-tight text-slate-100">{entry.title}</h4>
          <p className="text-sm text-slate-400 mt-1">{entry.description}</p>
          <div className="flex gap-2 mt-2">
            <span className={`text-xs px-2 py-1 rounded-lg inline-block ${statusBadge[entry.status] || 'bg-slate-700/50 border border-slate-600 text-slate-300'}`}>
              {statusLabels[entry.status] || entry.status}
            </span>
            <span className="text-xs bg-purple-500/15 border border-purple-500/40 text-purple-300 px-2 py-1 rounded-lg inline-block">
              T{entry.season ?? 1}
            </span>
            {entry.episode_published_at && (
              <span className="text-xs bg-emerald-500/15 border border-emerald-500/40 text-emerald-300 px-2 py-1 rounded-lg inline-block">
                Publicado
              </span>
            )}
            {entry.scheduled_date && (
              <span className="text-xs bg-slate-700/50 border border-slate-600 text-slate-300 px-2 py-1 rounded-lg inline-block">
                {new Date(entry.scheduled_date).toLocaleDateString('es-ES', {
                  day: 'numeric',
                  month: 'short',
                })}
              </span>
            )}
          </div>
          {entry.status === 'generated' && entry.audio_url && (
            <div className="mt-3">
              <audio controls preload="none" src={entry.audio_url} className="w-full h-8" />
            </div>
          )}
        </div>
        <div className="space-x-2 whitespace-nowrap">
          {entry.status === 'draft' && (
            <>
              <button
                type="button"
                onClick={() => onApprove(entry.id)}
                className="text-green-400 hover:text-green-300 hover:underline text-sm transition-colors"
              >
                Aprobar
              </button>
              <button
                type="button"
                onClick={() => onReject(entry.id)}
                className="text-amber-400 hover:text-amber-300 hover:underline text-sm transition-colors"
              >
                Rechazar
              </button>
            </>
          )}
          <button
            type="button"
            onClick={() => {
              setTitle(entry.title)
              setDescription(entry.description ?? '')
              setDate((entry.scheduled_date ?? '').slice(0, 10))
              setEditing(true)
            }}
            className="text-violet-400 hover:text-violet-300 hover:underline text-sm transition-colors"
          >
            Editar
          </button>
          <button
            type="button"
            onClick={() => onDelete(entry.id)}
            className="text-red-400 hover:text-red-300 hover:underline text-sm transition-colors"
          >
            Eliminar
          </button>
        </div>
      </div>
    </div>
  )
}
