import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useChannelStore } from '../stores/channelStore'
import { useAppStore } from '../stores/appStore'
import ChannelSelector from '../components/ChannelSelector'
import UploadScriptModal from '../components/UploadScriptModal'
import GenerateScriptWizard from '../components/GenerateScriptWizard'
import PlanTab from '../components/channel-hub/PlanTab'
import EpisodesTab from '../components/channel-hub/EpisodesTab'
import ConfigTab from '../components/channel-hub/ConfigTab'

type HubTab = 'plan' | 'episodios' | 'config'

export const Route = createFileRoute('/channels/$id')({
  validateSearch: (search: Record<string, unknown>): { tab?: HubTab } => ({
    tab: ['plan', 'episodios', 'config'].includes(search.tab as string)
      ? (search.tab as HubTab)
      : 'plan',
  }),
  component: ChannelHubPage,
})

function ChannelHubPage() {
  const { id } = Route.useParams()
  const { tab: tabParam } = Route.useSearch()
  const tab = tabParam ?? 'plan'
  const navigate = useNavigate()
  const channelId = Number(id)
  const {
    channels, error, fetchChannels, deleteChannel,
    publishChannel, unpublishChannel, fetchPlanEntries,
  } = useChannelStore()
  const askConfirm = useAppStore((s) => s.askConfirm)
  const [showUpload, setShowUpload] = useState(false)
  const [showWizard, setShowWizard] = useState(false)

  useEffect(() => {
    fetchChannels()
  }, [fetchChannels])

  useEffect(() => {
    fetchPlanEntries(channelId)
  }, [channelId, fetchPlanEntries])

  const channel = channels.find((c) => c.id === channelId)

  if (!channel) {
    return <div className="text-slate-400">Cargando canal...</div>
  }

  const handleDelete = async () => {
    const ok = await askConfirm({
      title: 'Eliminar canal',
      message: `¿Seguro que quieres eliminar "${channel.name}"? Esta acción no se puede deshacer.`,
      confirmLabel: 'Eliminar',
      danger: true,
    })
    if (ok) {
      await deleteChannel(channel.id)
      navigate({ to: '/channels' })
    }
  }

  return (
    <div>
      {/* Header del canal */}
      <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl shadow-lg shadow-black/20 mb-4">
        <div className="flex items-start gap-4 flex-wrap">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2 flex-wrap">
              <ChannelSelector
                channels={channels}
                value={channel.id}
                onChange={(newId) =>
                  navigate({ to: '/channels/$id', params: { id: String(newId) }, search: { tab } })
                }
                compact
              />
              <span className={`text-xs px-2 py-1 rounded-lg border ${channel.is_active ? 'bg-green-500/15 border-green-500/40 text-green-300' : 'bg-slate-700/50 border-slate-600 text-slate-400'}`}>
                {channel.is_active ? 'Activo' : 'Inactivo'}
              </span>
              {channel.autopilot && (
                <span className="text-xs px-2 py-1 rounded-lg border bg-violet-500/15 border-violet-500/40 text-violet-300" title="Piloto automático">🤖 Autopiloto</span>
              )}
              {channel.published_at && (
                <span className="text-xs px-2 py-1 rounded-lg border bg-emerald-500/15 border-emerald-500/40 text-emerald-300">Publicado</span>
              )}
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-100">{channel.name}</h2>
            <p className="text-sm text-slate-400 mt-1">{channel.description || 'Sin descripción'}</p>
            <p className="text-xs text-slate-500 mt-2">
              {channel.format} · nicho: {channel.niche || 'general'} · {channel.target_minutes} min · {channel.episodes_per_week} episodios/semana · {channel.num_speakers} voz{channel.num_speakers > 1 ? 'es' : ''}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setShowUpload(true)}
              className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors"
            >
              Cargar guion
            </button>
            <button
              type="button"
              onClick={() => setShowWizard(true)}
              className="bg-violet-600 text-white px-4 py-2 rounded-lg hover:bg-violet-500 transition-colors"
            >
              Generar guion con IA
            </button>
            {channel.published_at ? (
              <button type="button" onClick={() => unpublishChannel(channel.id)}
                className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg hover:bg-slate-600 transition-colors">
                Desmarcar publicado
              </button>
            ) : (
              <button type="button" onClick={() => publishChannel(channel.id)}
                className="bg-emerald-600 text-white px-4 py-2 rounded-lg hover:bg-emerald-500 transition-colors">
                Marcar publicado
              </button>
            )}
            <button type="button" onClick={handleDelete}
              className="bg-red-600/80 text-white px-4 py-2 rounded-lg hover:bg-red-500 transition-colors">
              Eliminar
            </button>
          </div>
        </div>
        {error && (
          <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg mt-4">Error: {error}</div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        {([['plan', 'Plan editorial'], ['episodios', 'Episodios'], ['config', 'Configuración']] as const).map(([key, label]) => (
          <button
            key={key}
            onClick={() => navigate({ to: '/channels/$id', params: { id }, search: { tab: key } })}
            className={`px-3 py-1 rounded-lg text-sm border ${
              tab === key
                ? 'bg-purple-600 border-purple-500 text-white'
                : 'bg-slate-800 border-slate-600 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 'plan' && <PlanTab channel={channel} />}
      {tab === 'episodios' && <EpisodesTab channel={channel} />}
      {tab === 'config' && <ConfigTab channel={channel} />}

      {showUpload && (
        <UploadScriptModal
          channel={channel}
          onClose={() => setShowUpload(false)}
          onUploaded={(episodeId) => navigate({ to: '/queue', search: { highlight: episodeId } })}
        />
      )}
      {showWizard && (
        <GenerateScriptWizard channel={channel} onClose={() => setShowWizard(false)} />
      )}
    </div>
  )
}
