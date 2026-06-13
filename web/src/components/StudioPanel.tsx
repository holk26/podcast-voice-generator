import { useState } from 'react'
import { Channel } from '../types'

interface Props {
  channels: Channel[]
  onGenerate: (channelId: number) => void
  loading: boolean
}

export default function StudioPanel({ channels, onGenerate, loading }: Props) {
  const [selectedId, setSelectedId] = useState<number | ''>(channels[0]?.id ?? '')

  return (
    <div className="bg-white p-6 rounded shadow">
      <h3 className="text-lg font-bold mb-4">CrewAI Studio</h3>
      <p className="text-sm text-gray-600 mb-4">
        Selecciona un canal y genera un plan editorial con IA.
      </p>
      <div className="flex gap-2">
        <select
          className="border rounded p-2"
          value={selectedId}
          onChange={(e) => setSelectedId(Number(e.target.value))}
        >
          {channels.map((c) => (
            <option key={c.id} value={c.id}>{c.name}</option>
          ))}
        </select>
        <button
          type="button"
          disabled={loading || selectedId === ''}
          onClick={() => onGenerate(Number(selectedId))}
          className="bg-purple-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {loading ? 'Generando...' : 'Generar plan'}
        </button>
      </div>
    </div>
  )
}
