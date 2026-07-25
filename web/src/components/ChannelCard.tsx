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
    <div className="bg-slate-800/50 border border-slate-700 p-4 rounded-xl shadow-lg shadow-black/20">
      <div className="flex justify-between items-start">
        <div>
          <h3 className="text-lg font-bold tracking-tight text-slate-100">
            {channel.name}
            {channel.autopilot && <span className="ml-2" title="Piloto automático">🤖</span>}
          </h3>
          <p className="text-sm text-slate-400">{channel.niche || 'Sin nicho'} • {channel.format}</p>
          <p className="text-sm text-slate-500 mt-1">{channel.description}</p>
        </div>
        <span className={`text-xs px-2 py-1 rounded-lg border ${channel.is_active ? 'bg-green-500/15 border-green-500/40 text-green-300' : 'bg-slate-700/50 border-slate-600 text-slate-400'}`}>
          {channel.is_active ? 'Activo' : 'Inactivo'}
        </span>
      </div>
      {total > 0 && (
        <div className="mt-3">
          <div className="flex justify-between text-xs text-slate-400 mb-1">
            <span>
              {generated}/{total} capítulos generados
            </span>
            <span>{pct}%</span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2">
            <div
              className="bg-green-500 h-2 rounded-full"
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      )}
      <div className="mt-4 space-x-2">
        <Link
          to="/channels/$id/plan"
          params={{ id: String(channel.id) }}
          className="text-purple-400 hover:text-purple-300 hover:underline text-sm transition-colors"
        >
          Ver plan
        </Link>
        <Link
          to="/channels/$id/edit"
          params={{ id: String(channel.id) }}
          className="text-violet-400 hover:text-violet-300 hover:underline text-sm transition-colors"
        >
          Editar
        </Link>
        <button
          type="button"
          onClick={() => onDelete(channel.id)}
          className="text-red-400 hover:text-red-300 hover:underline text-sm transition-colors"
        >
          Eliminar
        </button>
      </div>
    </div>
  )
}
