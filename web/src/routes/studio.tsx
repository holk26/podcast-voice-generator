import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useChannelStore } from '../stores/channelStore'
import { useVoiceStore } from '../stores/voiceStore'
import { api } from '../api/client'
import StudioPanel from '../components/StudioPanel'
import CrewJobActivity from '../components/CrewJobActivity'
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

  // Selecciona el primer canal cuando llegan los datos
  useEffect(() => {
    if (selectedId === '' && channels.length > 0) {
      setSelectedId(channels[0].id)
    }
  }, [channels, selectedId])

  // Carga el plan del canal seleccionado
  useEffect(() => {
    if (selectedId !== '') fetchPlanEntries(selectedId)
  }, [selectedId, fetchPlanEntries])

  const channel = channels.find((c) => c.id === selectedId)
  const channelEntries = selectedId === '' ? [] : entries[selectedId] || []

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Studio</h2>
      {llm && !llm.available && (
        <div className="bg-yellow-100 text-yellow-800 p-3 rounded mb-4">
          Ollama no está disponible — la generación con IA fallará. Arráncalo con{' '}
          <code className="bg-yellow-200 px-1 rounded">ollama serve</code>.
        </div>
      )}
      {llm?.available && llm.default_ready === false && (
        <div className="bg-yellow-100 text-yellow-800 p-3 rounded mb-4">
          El modelo {llm.default_model} no está descargado en Ollama. Ejecuta:{' '}
          <code className="bg-yellow-200 px-1 rounded">ollama pull {llm.default_model}</code>
        </div>
      )}
      {llm?.available && llm.default_ready && (
        <div className="bg-green-100 text-green-800 p-3 rounded mb-4">
          IA lista — Ollama con {llm.default_model}.
        </div>
      )}
      {error && (
        <div className="bg-red-100 text-red-800 p-3 rounded mb-4">Error: {error}</div>
      )}
      <CrewJobActivity />
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
        minutes={targetMinutes}
        onMinutesChange={setTargetMinutes}
        onGenerate={() => {
          if (channel) generatePlan(channel.id, count)
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
