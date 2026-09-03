import { useState } from 'react'
import { useChannelStore } from '../../stores/channelStore'
import ContentPlanList from '../ContentPlanList'
import PlanCalendar from '../PlanCalendar'
import CongressTable from '../CongressTable'
import LlmSelector from './LlmSelector'
import { Channel } from '../../types'

export default function PlanTab({ channel }: { channel: Channel }) {
  const {
    entries, loading, generatePlan, generateSeason,
    approveEntry, rejectEntry, deleteEntry,
  } = useChannelStore()
  const [count, setCount] = useState(5)
  const [seasonFilter, setSeasonFilter] = useState<number | null>(null)
  const [view, setView] = useState<'list' | 'calendar'>('list')

  const planEntries = entries[channel.id] || []
  const total = channel.entries_total ?? planEntries.length
  const generated = channel.entries_generated ?? planEntries.filter((e) => e.status === 'generated').length
  const pct = total > 0 ? Math.round((generated / total) * 100) : 0
  const seasons = [...new Set(planEntries.map((e) => e.season ?? 1))].sort((a, b) => a - b)
  const filtered = seasonFilter === null
    ? planEntries
    : planEntries.filter((e) => (e.season ?? 1) === seasonFilter)

  return (
    <div>
      <div className="flex justify-between items-center mb-4 flex-wrap gap-3">
        <LlmSelector />
        <div className="flex gap-2 items-center flex-wrap">
          <select
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-2 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
            title="Número de ideas"
          >
            {[3, 5, 8].map((n) => <option key={n} value={n}>{n} ideas</option>)}
          </select>
          <button
            type="button"
            disabled={loading}
            onClick={() => generatePlan(channel.id, count)}
            className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors disabled:opacity-50"
          >
            Generar con IA
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={() => generateSeason(channel.id, 4)}
            className="bg-violet-600 text-white px-4 py-2 rounded-lg hover:bg-violet-500 transition-colors disabled:opacity-50"
          >
            📅 Planificar temporada
          </button>
          <button
            type="button"
            onClick={() => setView(view === 'list' ? 'calendar' : 'list')}
            className="bg-slate-700 text-slate-100 px-4 py-2 rounded-lg hover:bg-slate-600 transition-colors"
          >
            {view === 'list' ? '📅 Calendario' : '📋 Lista'}
          </button>
        </div>
      </div>

      {total > 0 && (
        <div className="mb-4">
          <div className="flex justify-between text-sm text-slate-400 mb-1">
            <span>{generated}/{total} capítulos generados</span>
            <span>{pct}%</span>
          </div>
          <div className="w-full bg-slate-700 rounded-full h-2">
            <div className="bg-green-500 h-2 rounded-full" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}

      {seasons.length > 1 && (
        <div className="flex gap-2 mb-4 flex-wrap">
          <button type="button" onClick={() => setSeasonFilter(null)}
            className={`px-3 py-1 rounded-lg text-sm ${seasonFilter === null ? 'bg-purple-600 text-white' : 'bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700'}`}>
            Todas
          </button>
          {seasons.map((s) => (
            <button key={s} type="button" onClick={() => setSeasonFilter(s)}
              className={`px-3 py-1 rounded-lg text-sm ${seasonFilter === s ? 'bg-purple-600 text-white' : 'bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700'}`}>
              Temporada {s}
            </button>
          ))}
        </div>
      )}

      <CongressTable />

      {view === 'list' ? (
        <ContentPlanList entries={filtered} onApprove={approveEntry} onReject={rejectEntry} onDelete={deleteEntry} />
      ) : (
        <PlanCalendar entries={filtered} />
      )}
    </div>
  )
}
