import { Channel, Voice } from '../types'

interface Props {
  channels: Channel[]
  selectedId: number | ''
  onSelectChannel: (id: number) => void
  voices: Voice[]
  voiceId: string
  onVoiceChange: (voiceId: string) => void
  count: number
  onCountChange: (count: number) => void
  minutes: number
  onMinutesChange: (minutes: number) => void
  onGenerate: () => void
  loading: boolean
}

const COUNT_OPTIONS = [3, 5, 8]
const MINUTE_OPTIONS = [5, 10, 15]

export default function StudioPanel({
  channels,
  selectedId,
  onSelectChannel,
  voices,
  voiceId,
  onVoiceChange,
  count,
  onCountChange,
  minutes,
  onMinutesChange,
  onGenerate,
  loading,
}: Props) {
  return (
    <div className="bg-white p-6 rounded shadow mb-4">
      <h3 className="text-lg font-bold mb-4">CrewAI Studio</h3>
      <p className="text-sm text-gray-600 mb-4">
        Elige canal, voz y cuántas ideas quieres. El congreso de agentes genera el
        plan y, al aprobar una entrada, escribe el guion y crea el episodio.
      </p>
      <div className="flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-sm font-medium mb-1">Canal</label>
          <select
            className="border rounded p-2"
            value={selectedId}
            onChange={(e) => onSelectChannel(Number(e.target.value))}
          >
            {channels.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Voz de los episodios</label>
          <select
            className="border rounded p-2"
            value={voiceId}
            onChange={(e) => onVoiceChange(e.target.value)}
          >
            {voices.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name} ({v.engine})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Ideas</label>
          <select
            className="border rounded p-2"
            value={count}
            onChange={(e) => onCountChange(Number(e.target.value))}
          >
            {COUNT_OPTIONS.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Duración objetivo</label>
          <select
            className="border rounded p-2"
            value={minutes}
            onChange={(e) => onMinutesChange(Number(e.target.value))}
          >
            {MINUTE_OPTIONS.map((n) => (
              <option key={n} value={n}>{n} min</option>
            ))}
          </select>
        </div>
        <button
          type="button"
          disabled={loading || selectedId === ''}
          onClick={onGenerate}
          className="bg-purple-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {loading ? 'Generando...' : 'Generar plan'}
        </button>
      </div>
    </div>
  )
}
