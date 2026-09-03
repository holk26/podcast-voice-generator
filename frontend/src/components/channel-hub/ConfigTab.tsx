import { Channel } from '../../types'

export default function ConfigTab({ channel }: { channel: Channel }) {
  return <p className="text-slate-400">Configuración de {channel.name} (en construcción).</p>
}
