import { Link } from '@tanstack/react-router'
import { Channel } from '../types'

interface Props {
  channel: Channel
  onDelete: (id: number) => void
}

export default function ChannelCard({ channel, onDelete }: Props) {
  const total = channel.entries_total ?? 0
  const generated = channel.entries_generated ?? 0
  const pct = total > 0 ? Math.round((generated / total) * 100) : 0

  return (
    <div className="bg-white p-4 rounded shadow">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-bold">
            {channel.name}
            {channel.autopilot && <span className="ml-2" title="Piloto automático">🤖</span>}
          </h3>
          <p className="text-sm text-gray-600">{channel.niche || 'Sin nicho'} • {channel.format}</p>
          <p className="text-sm text-gray-500 mt-1">{channel.description}</p>
        </div>
        <span className={`text-xs px-2 py-1 rounded ${channel.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
          {channel.is_active ? 'Activo' : 'Inactivo'}
        </span>
      </div>
      {total > 0 && (
        <div className="mt-3">
          <div className="flex justify-between text-xs text-gray-600 mb-1">
            <span>
              {generated}/{total} capítulos generados
            </span>
            <span>{pct}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded h-2">
            <div
              className="bg-green-500 h-2 rounded"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}
      <div className="mt-4 space-x-2">
        <Link
          to="/channels/$id/plan"
          params={{ id: String(channel.id) }}
          className="text-blue-600 hover:underline text-sm"
        >
          Ver plan
        </Link>
        <Link
          to="/channels/$id/edit"
          params={{ id: String(channel.id) }}
          className="text-indigo-600 hover:underline text-sm"
        >
          Editar
        </Link>
        <button
          type="button"
          onClick={() => onDelete(channel.id)}
          className="text-red-600 hover:underline text-sm"
        >
          Eliminar
        </button>
      </div>
    </div>
  )
}
