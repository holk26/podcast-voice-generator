import { Channel, Voice } from '../types'
import ChannelSelector from './ChannelSelector'

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
  onGenerateSeason: () => void
  autopilot: boolean
  onAutopilotChange: (value: boolean) => void
  episodesPerWeek: number
  onEpisodesPerWeekChange: (value: number) => void
  loading: boolean
}

const COUNT_OPTIONS = [3, 5, 8]
const MINUTE_OPTIONS = [5, 10, 12, 15]
const WEEK_OPTIONS = [1, 2, 3]

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
  onGenerateSeason,
  autopilot,
  onAutopilotChange,
  episodesPerWeek,
  onEpisodesPerWeekChange,
  loading,
}: Props) {
  return (
    <div className="bg-slate-800/50 border border-slate-700 p-6 rounded-xl shadow-lg shadow-black/20 mb-4">
      <h3 className="text-lg font-bold tracking-tight mb-4">CrewAI Studio</h3>
      <p className="text-sm text-slate-400 mb-4">
        Elige canal, voz y duración. El showrunner diseña temporadas completas y,
        con el piloto automático, el congreso escribe y produce los episodios solo.
      </p>
      <div className="flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-sm font-medium text-slate-200 mb-1">Canal</label>
          <ChannelSelector
            channels={channels}
            value={selectedId}
            onChange={onSelectChannel}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-200 mb-1">Voz</label>
          <select
            className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
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
          <label className="block text-sm font-medium text-slate-200 mb-1">Ideas</label>
          <select
            className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
            value={count}
            onChange={(e) => onCountChange(Number(e.target.value))}
          >
            {COUNT_OPTIONS.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-200 mb-1">Duración</label>
          <select
            className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-purple-500"
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
          className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Generar plan
        </button>
        <button
          type="button"
          disabled={loading || selectedId === ''}
          onClick={onGenerateSeason}
          className="bg-violet-600 text-white px-4 py-2 rounded-lg hover:bg-violet-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          📅 Planificar temporada
        </button>
      </div>

      <div className="flex flex-wrap gap-4 items-center mt-4 pt-4 border-t border-slate-700">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={autopilot}
            onChange={(e) => onAutopilotChange(e.target.checked)}
            className="w-4 h-4 accent-purple-500"
          />
          <span className="text-sm font-medium text-slate-200">🤖 Piloto automático</span>
        </label>
        <div>
          <label className="block text-sm font-medium text-slate-200 mb-1">Episodios/semana</label>
          <select
            className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 focus:outline-none focus:ring-2 focus:ring-purple-500 disabled:opacity-50"
            value={episodesPerWeek}
            onChange={(e) => onEpisodesPerWeekChange(Number(e.target.value))}
            disabled={!autopilot}
          >
            {WEEK_OPTIONS.map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
        {autopilot && (
          <p className="text-sm text-slate-400">
            El congreso generará temporadas y episodios de este canal sin intervención.
          </p>
        )}
      </div>
    </div>
  )
}
