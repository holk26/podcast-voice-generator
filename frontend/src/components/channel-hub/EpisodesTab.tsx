import { Channel } from '../../types'

export default function EpisodesTab({ channel }: { channel: Channel }) {
  return <p className="text-slate-400">Episodios de {channel.name} (en construcción).</p>
}
