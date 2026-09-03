import { Channel } from '../../types'

export default function PlanTab({ channel }: { channel: Channel }) {
  return <p className="text-slate-400">Plan editorial de {channel.name} (en construcción).</p>
}
