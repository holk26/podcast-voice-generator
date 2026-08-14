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
    return <p className="text-slate-400">No hay episodios con fecha programada.</p>
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
          <div key={monday} className="bg-slate-800/50 border border-slate-700 rounded-xl shadow-lg shadow-black/20 p-4">
            <h4 className="font-bold tracking-tight text-purple-300 mb-2">
              Semana del {fmt(weekStart)} al {fmt(weekEnd)}
            </h4>
            <ul className="divide-y divide-slate-700/60">
              {weekEntries.map((e) => (
                <li key={e.id} className="py-2 flex items-center gap-3">
                  <span className="text-xs bg-slate-700/50 border border-slate-600 text-slate-300 px-2 py-1 rounded-lg w-16 text-center">
                    {new Date(e.scheduled_date!).toLocaleDateString('es-ES', {
                      weekday: 'short',
                      day: 'numeric',
                    })}
                  </span>
                  <span className="text-xs bg-purple-500/15 border border-purple-500/40 text-purple-300 px-1.5 py-0.5 rounded-lg">
                    T{e.season ?? 1}
                  </span>
                  <span className="flex-1 font-medium text-slate-100">{e.title}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-lg border ${
                      e.status === 'generated'
                        ? 'bg-green-500/15 border-green-500/40 text-green-300'
                        : e.status === 'rejected'
                          ? 'bg-slate-700/50 border-slate-600 text-slate-400'
                          : 'bg-amber-500/15 border-amber-500/40 text-amber-300'
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
