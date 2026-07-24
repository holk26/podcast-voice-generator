import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useChannelStore } from '../stores/channelStore'
import { useVoiceStore } from '../stores/voiceStore'
import { api } from '../api/client'
import StudioPanel from '../components/StudioPanel'
import CongressTable from '../components/CongressTable'
import ContentPlanList from '../components/ContentPlanList'

export const Route = createFileRoute('/studio')({
  component: StudioPage,
})

interface LlmStatus {
  available: boolean
  default_ready?: boolean
  default_model?: string
  error?: string
}

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
  const [llm, setLlm] = useState<LlmStatus | null>(null)
  const [selectedId, setSelectedId] = useState<number | ''>('')
  const [count, setCount] = useState(5)

  useEffect(() => {
    fetchChannels()
    fetchVoices()
    api.getLlmStatus().then(setLlm).catch(() => setLlm({ available: false }))
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
  const llmOk = llm?.available && llm.default_ready

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <h2 className="text-2xl font-bold">Studio</h2>
        {llm && (
          <span
            className={`text-xs px-2 py-1 rounded ${
              llmOk ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
            }`}
            title={llmOk ? undefined : 'Arranca Ollama o descarga el modelo'}
          >
            {llmOk ? `● IA lista (${llm.default_model})` : '● IA no disponible'}
          </span>
        )}
      </div>

      <CongressTable />

      {error && (
        <div className="bg-red-100 text-red-800 p-3 rounded mb-4">Error: {error}</div>
      )}

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

      {channel && (
        <div>
          <h3 className="text-lg font-bold mb-2">Plan editorial de {channel.name}</h3>
          <ContentPlanList
            entries={channelEntries}
            onApprove={approveEntry}
            onReject={rejectEntry}
            onDelete={deleteEntry}
          />
        </div>
      )}
    </div>
  )
}
