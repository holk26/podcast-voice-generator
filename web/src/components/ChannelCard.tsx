import { Link } from '@tanstack/react-router'
import { Channel } from '../types'

interface Props {
  channel: Channel
  onDelete: (id: number) => void
}

export default function ChannelCard({ channel, onDelete }: Props) {
  return (
    <div className="bg-white p-4 rounded shadow">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-bold">{channel.name}</h3>
          <p className="text-sm text-gray-600">{channel.niche || 'Sin nicho'} • {channel.format}</p>
          <p className="text-sm text-gray-500 mt-1">{channel.description}</p>
        </div>
        <span className={`text-xs px-2 py-1 rounded ${channel.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
          {channel.is_active ? 'Activo' : 'Inactivo'}
        </span>
      </div>
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
