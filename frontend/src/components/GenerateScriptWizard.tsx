import { Channel } from '../types'

export default function GenerateScriptWizard({ channel, onClose }: { channel: Channel; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl p-6">
        <p className="text-slate-300">Wizard de {channel.name} (en construcción).</p>
        <button onClick={onClose} className="mt-4 bg-slate-700 px-4 py-2 rounded-lg text-white">Cerrar</button>
      </div>
    </div>
  )
}
