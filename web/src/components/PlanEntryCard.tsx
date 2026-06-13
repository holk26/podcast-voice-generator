import { ContentPlanEntry } from '../types'

interface Props {
  entry: ContentPlanEntry
  onApprove: (id: number) => void
  onReject: (id: number) => void
  onDelete: (id: number) => void
}

const statusLabels: Record<string, string> = {
  draft: 'Borrador',
  generated: 'Generado',
  rejected: 'Rechazado',
}

export default function PlanEntryCard({ entry, onApprove, onReject, onDelete }: Props) {
  return (
    <div className="bg-white p-4 rounded shadow border-l-4 border-blue-500">
      <div className="flex justify-between items-start">
        <div>
          <h4 className="font-bold">{entry.title}</h4>
          <p className="text-sm text-gray-600 mt-1">{entry.description}</p>
          <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded mt-2 inline-block">
            {statusLabels[entry.status] || entry.status}
          </span>
        </div>
        <div className="space-x-2">
          {entry.status === 'draft' && (
            <>
              <button
                type="button"
                onClick={() => onApprove(entry.id)}
                className="text-green-600 hover:underline text-sm"
              >
                Aprobar
              </button>
              <button
                type="button"
                onClick={() => onReject(entry.id)}
                className="text-yellow-600 hover:underline text-sm"
              >
                Rechazar
              </button>
            </>
          )}
          <button
            type="button"
            onClick={() => onDelete(entry.id)}
            className="text-red-600 hover:underline text-sm"
          >
            Eliminar
          </button>
        </div>
      </div>
    </div>
  )
}
