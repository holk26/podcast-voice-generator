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
      <div className="bg-white p-4 rounded shadow border-l-4 border-indigo-500 space-y-2">
        <input
          className="w-full border rounded p-2 font-bold"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          className="w-full border rounded p-2 text-sm"
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Fecha:</label>
          <input
            type="date"
            className="border rounded p-1 text-sm"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>
        <div className="space-x-2">
          <button
            type="button"
            onClick={handleSave}
            className="bg-indigo-600 text-white px-3 py-1 rounded text-sm"
          >
            Guardar
          </button>
          <button
            type="button"
            onClick={() => setEditing(false)}
            className="bg-gray-300 px-3 py-1 rounded text-sm"
          >
            Cancelar
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white p-4 rounded shadow border-l-4 border-blue-500">
      <div className="flex justify-between items-start">
        <div className="flex-1 min-w-0">
          <h4 className="font-bold">{entry.title}</h4>
          <p className="text-sm text-gray-600 mt-1">{entry.description}</p>
          <div className="flex gap-2 mt-2">
            <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded inline-block">
              {statusLabels[entry.status] || entry.status}
            </span>
            <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded inline-block">
              T{entry.season ?? 1}
            </span>
            {entry.scheduled_date && (
              <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded inline-block">
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
                className="text-green-600 hover:underline text-sm"
              >
                Aprobar
              </button>
              <button
                type="button"
                onClick={() => onReject(entry.id)}
                className="text-yellow-600 hover:underline text-sm"
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
            className="text-indigo-600 hover:underline text-sm"
          >
            Editar
          </button>
          <button
            type="button"
            onClick={() => onDelete(entry.id)}
            className="text-red-600 hover:underline text-sm"
          >
            Eliminar
          </button>
        </div>
      </div>
    </div>
  )
}
