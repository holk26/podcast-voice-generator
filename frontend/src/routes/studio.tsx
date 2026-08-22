import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useChannelStore } from '../stores/channelStore'
import { useVoiceStore } from '../stores/voiceStore'
import { api } from '../api/client'
import StudioPanel from '../components/StudioPanel'
import ContentPlanList from '../components/ContentPlanList'
import PlanEntryCard from '../components/PlanEntryCard'
import { CreateChannelRequest, LlmProvider } from '../types'

export const Route = createFileRoute('/studio')({
  component: StudioPage,
})

type StudioTab = 'overview' | 'plan' | 'config'

function StudioPage() {
  const {
    channels,
    entries,
    loading,
    error,
    fetchChannels,
    updateChannel,
    fetchPlanEntries,
    generatePlan,
    generateSeason,
    approveEntry,
    rejectEntry,
    deleteEntry,
    targetMinutes,
    setTargetMinutes,
  } = useChannelStore()
  const { voices, fetchVoices } = useVoiceStore()
  const [providers, setProviders] = useState<LlmProvider[]>([])
  const [currentProvider, setCurrentProvider] = useState<string>('')
  const [modelsByProvider, setModelsByProvider] = useState<Record<string, string[]>>({})
  const [currentModel, setCurrentModel] = useState<string>('')
  const [selectedId, setSelectedId] = useState<number | ''>('')
  const [count, setCount] = useState(5)
  const [tab, setTab] = useState<StudioTab>('overview')

  useEffect(() => {
    fetchChannels()
    fetchVoices()
    api.getLlmProviders()
      .then((d) => {
        setProviders(d.providers)
        setCurrentProvider(d.current_provider)
        setCurrentModel(d.current_model)
        d.providers.forEach((p) => {
          if (!p.available) return
          api.getLlmModels(p.id)
            .then((m) => {
              setModelsByProvider((prev) => ({ ...prev, [m.provider]: m.models }))
              if (p.id === d.current_provider && !m.models.includes(d.current_model)) {
                setCurrentModel(m.models[0] || '')
              }
            })
            .catch(() => {})
        })
      })
      .catch(() => setProviders([]))
  }, [fetchChannels, fetchVoices])

  useEffect(() => {
    if (selectedId === '' && channels.length > 0) {
      setSelectedId(channels[0].id)
    }
  }, [channels, selectedId])

  useEffect(() => {
    if (selectedId !== '') fetchPlanEntries(selectedId)
  }, [selectedId, fetchPlanEntries])

  const channel = channels.find((c) => c.id === selectedId)
  const channelEntries = selectedId === '' ? [] : entries[selectedId] || []
  const activeProvider = providers.find((p) => p.id === currentProvider)
  const llmOk = activeProvider?.available ?? false
  const latestEntries = [...channelEntries]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 3)

  return (
    <div>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <h2 className="text-2xl font-bold tracking-tight">Studio</h2>
        {activeProvider && (
          <span
            className={`text-xs px-2 py-1 rounded-lg border ${
              llmOk
                ? 'bg-green-500/15 border-green-500/40 text-green-300'
                : 'bg-amber-500/15 border-amber-500/40 text-amber-300'
            }`}
            title={llmOk ? undefined : 'Provider no disponible'}
          >
            {llmOk ? `● ${activeProvider.name} lista` : `● ${activeProvider.name} no disponible`}
          </span>
        )}
        <label className="flex items-center gap-1 text-xs text-slate-400">
          Provider:
          <select
            className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-1 py-0.5 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
            value={currentProvider}
            onChange={async (e) => {
              const provider = e.target.value
              setCurrentProvider(provider)
              const models = modelsByProvider[provider] || []
              const model = models[0] || ''
              setCurrentModel(model)
              if (model) await api.setLlmModel(provider, model)
            }}
          >
            {providers.map((p) => (
              <option key={p.id} value={p.id} disabled={!p.available}>
                {p.name} {!p.available ? '(no configurado)' : ''}
              </option>
            ))}
          </select>
        </label>
        {currentProvider && (modelsByProvider[currentProvider]?.length ?? 0) > 0 && (
          <label className="flex items-center gap-1 text-xs text-slate-400">
            Modelo:
            <select
              className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-1 py-0.5 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
              value={currentModel}
              onChange={async (e) => {
                const model = e.target.value
                setCurrentModel(model)
                await api.setLlmModel(currentProvider, model)
              }}
            >
              {modelsByProvider[currentProvider]?.map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </label>
        )}
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg mb-4">Error: {error}</div>
      )}

      {channel && (
        <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl shadow-lg shadow-black/20 mb-4">
          <div className="flex justify-between items-start gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-3 mb-2">
                <select
                  className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                  value={selectedId}
                  onChange={(e) => setSelectedId(Number(e.target.value))}
                >
                  {channels.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
                <Link
                  to="/channels/$id/edit"
                  params={{ id: String(channel.id) }}
                  className="text-violet-400 hover:text-violet-300 hover:underline text-sm transition-colors whitespace-nowrap"
                >
                  Editar canal
                </Link>
              </div>
              <h3 className="text-lg font-bold tracking-tight text-slate-100">{channel.name}</h3>
              <p className="text-sm text-slate-400 mt-1">{channel.description || 'Sin descripción'}</p>
              <p className="text-xs text-slate-500 mt-2">
                {channel.format} · nicho: {channel.niche || 'general'} · {channel.target_minutes} min · {channel.episodes_per_week} episodios/semana · {channel.num_speakers} voz{channel.num_speakers > 1 ? 'es' : ''}
              </p>
            </div>
          </div>
        </div>
      )}

      {channel && (
        <div className="flex gap-2 mb-4">
          {(['overview', 'plan', 'config'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3 py-1 rounded-lg text-sm border ${
                tab === t
                  ? 'bg-purple-600 border-purple-500 text-white'
                  : 'bg-slate-800 border-slate-600 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {t === 'overview' ? 'Resumen' : t === 'plan' ? 'Plan editorial' : 'Configuración'}
            </button>
          ))}
        </div>
      )}

      {tab === 'overview' && channel && (
        <div className="space-y-4">
          <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl shadow-lg shadow-black/20">
            <h4 className="text-md font-bold tracking-tight text-slate-200 mb-3">Configuración rápida</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <label className="block">
                <span className="text-sm text-slate-400">Número de voces</span>
                <select
                  className="mt-1 w-full bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                  value={channel.num_speakers}
                  onChange={(e) => {
                    const n = Number(e.target.value)
                    const updates: Partial<CreateChannelRequest> = { num_speakers: n }
                    if (n === 1) {
                      updates.speaker_voices = null
                    } else if (!channel.speaker_voices || Object.keys(channel.speaker_voices).length === 0) {
                      updates.speaker_voices = {
                        'Narrador': channel.default_voice_id,
                        'Invitado': channel.default_voice_id,
                      }
                    }
                    updateChannel(channel.id, updates)
                  }}
                >
                  <option value={1}>1 voz (monólogo)</option>
                  <option value={2}>2 voces (diálogo)</option>
                </select>
              </label>

              {channel.num_speakers === 1 ? (
                <label className="block">
                  <span className="text-sm text-slate-400">Voz del canal</span>
                  <select
                    className="mt-1 w-full bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                    value={channel.default_voice_id}
                    onChange={(e) => updateChannel(channel.id, { default_voice_id: e.target.value })}
                  >
                    {voices.map((v) => (
                      <option key={v.id} value={v.id}>
                        {v.type === 'cloned' ? '🎙️ ' : ''}{v.name}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <div className="block md:col-span-2">
                  <span className="text-sm text-slate-400">Voces del diálogo</span>
                  <div className="mt-2 space-y-2">
                    {Object.entries(channel.speaker_voices || {}).map(([speaker, voiceId]) => (
                      <div key={speaker} className="flex gap-2 items-center">
                        <input
                          className="w-32 bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                          value={speaker}
                          onChange={(e) => {
                            const newVoices = { ...(channel.speaker_voices || {}) }
                            delete newVoices[speaker]
                            newVoices[e.target.value] = voiceId
                            updateChannel(channel.id, { speaker_voices: newVoices })
                          }}
                        />
                        <select
                          className="flex-1 bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                          value={voiceId}
                          onChange={(e) => {
                            updateChannel(channel.id, {
                              speaker_voices: { ...(channel.speaker_voices || {}), [speaker]: e.target.value },
                            })
                          }}
                        >
                          {voices.map((v) => (
                            <option key={v.id} value={v.id}>
                              {v.type === 'cloned' ? '🎙️ ' : ''}{v.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <label className="block">
                <span className="text-sm text-slate-400">Duración objetivo (min)</span>
                <input
                  type="number"
                  min={2}
                  max={30}
                  className="mt-1 w-full bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                  value={channel.target_minutes}
                  onChange={(e) => updateChannel(channel.id, { target_minutes: Number(e.target.value) })}
                />
              </label>
              <label className="block">
                <span className="text-sm text-slate-400">Episodios por semana</span>
                <input
                  type="number"
                  min={1}
                  max={7}
                  className="mt-1 w-full bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                  value={channel.episodes_per_week}
                  onChange={(e) => updateChannel(channel.id, { episodes_per_week: Number(e.target.value) })}
                />
              </label>
              <label className="flex items-end gap-2 pb-2">
                <input
                  type="checkbox"
                  className="rounded border-slate-600 bg-slate-800 text-purple-600 focus:ring-purple-500"
                  checked={channel.autopilot}
                  onChange={(e) => updateChannel(channel.id, { autopilot: e.target.checked })}
                />
                <span className="text-sm text-slate-300">Piloto automático</span>
              </label>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={loading}
              onClick={() => generatePlan(channel.id, count)}
              className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Generar {count} ideas
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => generateSeason(channel.id, 4)}
              className="bg-violet-600 text-white px-4 py-2 rounded-lg hover:bg-violet-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              📅 Planificar temporada
            </button>
          </div>

          {latestEntries.length > 0 && (
            <div>
              <h4 className="text-md font-bold tracking-tight text-slate-200 mb-2">Últimas entradas</h4>
              <div className="space-y-3">
                {latestEntries.map((entry) => (
                  <PlanEntryCard
                    key={entry.id}
                    entry={entry}
                    onApprove={approveEntry}
                    onReject={rejectEntry}
                    onDelete={deleteEntry}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {tab === 'plan' && channel && (
        <div>
          <h3 className="text-lg font-bold tracking-tight mb-2">Plan editorial de {channel.name}</h3>
          <ContentPlanList
            entries={channelEntries}
            onApprove={approveEntry}
            onReject={rejectEntry}
            onDelete={deleteEntry}
          />
        </div>
      )}

      {tab === 'config' && (
        <StudioPanel
          channels={channels}
          selectedId={selectedId}
          onSelectChannel={setSelectedId}
          voices={voices}
          voiceId={channel?.default_voice_id ?? 'jorge'}
          onVoiceChange={(voiceId) => {
            if (channel) updateChannel(channel.id, { default_voice_id: voiceId })
          }}
          count={count}
          onCountChange={setCount}
          minutes={channel?.target_minutes ?? targetMinutes}
          onMinutesChange={(m) => {
            setTargetMinutes(m)
            if (channel) updateChannel(channel.id, { target_minutes: m })
          }}
          onGenerate={() => {
            if (channel) generatePlan(channel.id, count)
          }}
          onGenerateSeason={() => {
            if (channel) generateSeason(channel.id, 4)
          }}
          autopilot={channel?.autopilot ?? false}
          onAutopilotChange={(v) => {
            if (channel) updateChannel(channel.id, { autopilot: v })
          }}
          episodesPerWeek={channel?.episodes_per_week ?? 2}
          onEpisodesPerWeekChange={(v) => {
            if (channel) updateChannel(channel.id, { episodes_per_week: v })
          }}
          loading={loading}
        />
      )}
    </div>
  )
}
