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
  if (entries.length === 0) return <p className="text-slate-400">No hay entradas en el plan.</p>

  const drafts = entries.filter((e) => e.status === 'draft')
  const archive = entries.filter((e) => e.status !== 'draft')

  const seasons = new Map<number, ContentPlanEntry[]>()
  drafts.forEach((entry) => {
    const list = seasons.get(entry.season ?? 1) ?? []
    list.push(entry)
    seasons.set(entry.season ?? 1, list)
  })
  const sortedSeasons = [...seasons.entries()].sort((a, b) => b[0] - a[0])

  return (
    <div className="space-y-6">
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
