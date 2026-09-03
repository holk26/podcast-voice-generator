import { useState } from 'react'
import { Link, useNavigate } from '@tanstack/react-router'
import { Channel } from '../types'
import { useChannelStore } from '../stores/channelStore'
import { useAppStore } from '../stores/appStore'
import UploadScriptModal from './UploadScriptModal'

interface Props {
  channel: Channel
  onDelete: (id: number) => void
}

export default function ChannelCard({ channel, onDelete }: Props) {
  const publishChannel = useChannelStore((s) => s.publishChannel)
  const unpublishChannel = useChannelStore((s) => s.unpublishChannel)
  const askConfirm = useAppStore((s) => s.askConfirm)
  const navigate = useNavigate()
  const [showUpload, setShowUpload] = useState(false)

  const handleDelete = async () => {
    const ok = await askConfirm({
      title: 'Eliminar canal',
      message: `¿Seguro que quieres eliminar "${channel.name}"? Esta acción no se puede deshacer.`,
      confirmLabel: 'Eliminar',
      danger: true,
    })
    if (ok) onDelete(channel.id)
  }
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
        <div className="flex gap-2">
          {channel.published_at && (
            <span className="text-xs px-2 py-1 rounded-lg border bg-emerald-500/15 border-emerald-500/40 text-emerald-300">
              Publicado
            </span>
          )}
          <span className={`text-xs px-2 py-1 rounded-lg border ${channel.is_active ? 'bg-green-500/15 border-green-500/40 text-green-300' : 'bg-slate-700/50 border-slate-600 text-slate-400'}`}>
            {channel.is_active ? 'Activo' : 'Inactivo'}
          </span>
        </div>
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
      <div className="mt-4 flex flex-wrap gap-4">
        <button
          type="button"
          onClick={() => setShowUpload(true)}
          className="text-purple-400 hover:text-purple-300 hover:underline text-sm transition-colors"
        >
          Cargar guion
        </button>
        <Link
          to="/channels/$id"
          params={{ id: String(channel.id) }}
          search={{ tab: 'plan' }}
          className="text-violet-400 hover:text-violet-300 hover:underline text-sm transition-colors"
        >
          Ver plan
        </Link>
        <Link
          to="/channels/$id"
          params={{ id: String(channel.id) }}
          search={{ tab: 'config' }}
          className="text-violet-400 hover:text-violet-300 hover:underline text-sm transition-colors"
        >
          Editar
        </Link>
        {channel.published_at ? (
          <button
            type="button"
            onClick={() => unpublishChannel(channel.id)}
            className="text-slate-400 hover:text-slate-300 text-sm hover:underline transition-colors"
          >
            Desmarcar publicado
          </button>
        ) : (
          <button
            type="button"
            onClick={() => publishChannel(channel.id)}
            className="text-emerald-400 hover:text-emerald-300 text-sm hover:underline transition-colors"
          >
            Marcar publicado
          </button>
        )}
        <button
          type="button"
          onClick={() => handleDelete()}
          className="text-red-400 hover:text-red-300 hover:underline text-sm transition-colors"
        >
          Eliminar
        </button>
      </div>

      {showUpload && (
        <UploadScriptModal
          channel={channel}
          onClose={() => setShowUpload(false)}
          onUploaded={(episodeId) => navigate({ to: '/queue', search: { highlight: episodeId } })}
        />
      )}
    </div>
  )
}
