import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useChannelStore } from '../stores/channelStore'
import { api } from '../api/client'
import StudioPanel from '../components/StudioPanel'
import CrewJobActivity from '../components/CrewJobActivity'

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
  const { channels, loading, error, fetchChannels, generatePlan } = useChannelStore()
  const [llm, setLlm] = useState<LlmStatus | null>(null)

  useEffect(() => {
    fetchChannels()
    api.getLlmStatus().then(setLlm).catch(() => setLlm({ available: false }))
  }, [fetchChannels])

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
      <StudioPanel channels={channels} onGenerate={generatePlan} loading={loading} />
    </div>
  )
}
