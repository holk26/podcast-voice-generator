import { useState } from 'react'
import { ContentPlanEntry } from '../types'
import PlanEntryCard from './PlanEntryCard'

interface Props {
  entries: ContentPlanEntry[]
  onApprove: (id: number) => void
  onReject: (id: number) => void
  onDelete: (id: number) => void
}

export default function ContentPlanList({ entries, onApprove, onReject, onDelete }: Props) {
  const [showArchive, setShowArchive] = useState(false)
  const [recentOnly, setRecentOnly] = useState(true)
  if (entries.length === 0) return <p className="text-slate-400">No hay entradas en el plan.</p>

  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - 30)

  const sorted = [...entries].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )

  const drafts = sorted
    .filter((e) => e.status === 'draft')
    .filter((e) => !recentOnly || !e.created_at || new Date(e.created_at) >= cutoff)
  const archive = sorted.filter((e) => e.status !== 'draft')

  const seasons = new Map<number, ContentPlanEntry[]>()
  drafts.forEach((entry) => {
    const list = seasons.get(entry.season ?? 1) ?? []
    list.push(entry)
    seasons.set(entry.season ?? 1, list)
  })
  const sortedSeasons = [...seasons.entries()].sort((a, b) => b[0] - a[0])

  return (
    <div className="space-y-6">
      <div className="flex justify-end">
        <label className="flex items-center gap-2 text-sm text-slate-400">
          <input
            type="checkbox"
            checked={recentOnly}
            onChange={(e) => setRecentOnly(e.target.checked)}
            className="w-4 h-4 accent-purple-500"
          />
          Solo últimos 30 días
        </label>
      </div>
      {drafts.length === 0 && (
        <p className="text-slate-400">Sin borradores pendientes. Genera un plan o una temporada.</p>
      )}
      {sortedSeasons.map(([season, seasonEntries]) => (
        <section key={season}>
          <div className="flex items-center gap-3 mb-2">
            <h3 className="text-md font-bold tracking-tight text-purple-300">Temporada {season}</h3>
            <span className="text-xs text-slate-400">{seasonEntries.length} borradores</span>
          </div>
          <div className="space-y-3">
            {seasonEntries.map((entry) => (
              <PlanEntryCard
                key={entry.id}
                entry={entry}
                onApprove={onApprove}
                onReject={onReject}
                onDelete={onDelete}
              />
            ))}
          </div>
        </section>
      ))}

      {archive.length > 0 && (
        <section>
          <button
            type="button"
            onClick={() => setShowArchive((v) => !v)}
            className="text-sm text-slate-400 hover:text-slate-300 transition-colors"
          >
            {showArchive ? '▾' : '▸'} Archivo ({archive.length} generadas/rechazadas)
          </button>
          {showArchive && (
            <div className="space-y-3 mt-3">
              {archive.map((entry) => (
                <PlanEntryCard
                  key={entry.id}
                  entry={entry}
                  onApprove={onApprove}
                  onReject={onReject}
                  onDelete={onDelete}
                />
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  )
}
