import { ContentPlanEntry } from '../types'
import PlanEntryCard from './PlanEntryCard'

interface Props {
  entries: ContentPlanEntry[]
  onApprove: (id: number) => void
  onReject: (id: number) => void
  onDelete: (id: number) => void
}

export default function ContentPlanList({ entries, onApprove, onReject, onDelete }: Props) {
  if (entries.length === 0) return <p className="text-gray-500">No hay entradas en el plan.</p>

  // Agrupa por temporada (las más recientes primero)
  const seasons = new Map<number, ContentPlanEntry[]>()
  entries.forEach((entry) => {
    const list = seasons.get(entry.season ?? 1) ?? []
    list.push(entry)
    seasons.set(entry.season ?? 1, list)
  })
  const sortedSeasons = [...seasons.entries()].sort((a, b) => b[0] - a[0])

  return (
    <div className="space-y-6">
      {sortedSeasons.map(([season, seasonEntries]) => {
        const generated = seasonEntries.filter((e) => e.status === 'generated').length
        return (
          <section key={season}>
            <div className="flex items-center gap-3 mb-2">
              <h3 className="text-md font-bold text-purple-800">Temporada {season}</h3>
              <span className="text-xs text-gray-500">
                {generated}/{seasonEntries.length} generados
              </span>
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
        )
      })}
    </div>
  )
}
