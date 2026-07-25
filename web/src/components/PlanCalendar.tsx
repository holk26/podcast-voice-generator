import { ContentPlanEntry } from '../types'

interface Props {
  entries: ContentPlanEntry[]
}

/** Vista calendario semanal del plan editorial. */
export default function PlanCalendar({ entries }: Props) {
  const scheduled = entries
    .filter((e) => e.scheduled_date)
    .sort((a, b) => (a.scheduled_date! > b.scheduled_date! ? 1 : -1))

  if (scheduled.length === 0) {
    return <p className="text-gray-500">No hay episodios con fecha programada.</p>
  }

  // Agrupa por semana (lunes)
  const weeks = new Map<string, ContentPlanEntry[]>()
  scheduled.forEach((e) => {
    const d = new Date(e.scheduled_date!)
    const monday = new Date(d)
    monday.setDate(d.getDate() - ((d.getDay() + 6) % 7))
    const key = monday.toISOString().slice(0, 10)
    const list = weeks.get(key) ?? []
    list.push(e)
    weeks.set(key, list)
  })

  return (
    <div className="space-y-4">
      {[...weeks.entries()].map(([monday, weekEntries]) => {
        const weekStart = new Date(monday)
        const weekEnd = new Date(weekStart)
        weekEnd.setDate(weekStart.getDate() + 6)
        const fmt = (d: Date) =>
          d.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' })
        return (
          <div key={monday} className="bg-white rounded shadow p-4">
            <h4 className="font-bold text-purple-800 mb-2">
              Semana del {fmt(weekStart)} al {fmt(weekEnd)}
            </h4>
            <ul className="divide-y">
              {weekEntries.map((e) => (
                <li key={e.id} className="py-2 flex items-center gap-3">
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded w-16 text-center">
                    {new Date(e.scheduled_date!).toLocaleDateString('es-ES', {
                      weekday: 'short',
                      day: 'numeric',
                    })}
                  </span>
                  <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">
                    T{e.season ?? 1}
                  </span>
                  <span className="flex-1 font-medium">{e.title}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded ${
                      e.status === 'generated'
                        ? 'bg-green-100 text-green-700'
                        : e.status === 'rejected'
                          ? 'bg-gray-100 text-gray-500'
                          : 'bg-yellow-100 text-yellow-700'
                    }`}
                  >
                    {e.status === 'generated'
                      ? '✓ listo'
                      : e.status === 'rejected'
                        ? 'rechazado'
                        : 'pendiente'}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </div>
  )
}
