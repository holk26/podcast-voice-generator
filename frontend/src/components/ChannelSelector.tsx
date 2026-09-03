import { Channel } from '../types'

interface Props {
  channels: Channel[]
  value: number | ''
  onChange: (id: number) => void
  compact?: boolean
}

export default function ChannelSelector({ channels, value, onChange, compact }: Props) {
  const cls = compact
    ? 'bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500'
    : 'bg-slate-800 border border-slate-600 text-slate-100 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500'
  return (
    <select
      className={cls}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      aria-label="Seleccionar canal"
    >
      {channels.map((c) => (
        <option key={c.id} value={c.id}>{c.name}</option>
      ))}
    </select>
  )
}
