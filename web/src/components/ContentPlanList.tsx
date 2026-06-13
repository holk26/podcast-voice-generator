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
  return (
    <div className="space-y-3">
      {entries.map((entry) => (
        <PlanEntryCard
          key={entry.id}
          entry={entry}
          onApprove={onApprove}
          onReject={onReject}
          onDelete={onDelete}
        />
      ))}
    </div>
  )
}
