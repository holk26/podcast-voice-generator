import { useEffect, useState } from 'react'
import { api } from '../../api/client'
import { LlmProvider } from '../../types'

export default function LlmSelector() {
  const [providers, setProviders] = useState<LlmProvider[]>([])
  const [currentProvider, setCurrentProvider] = useState<string>('')
  const [modelsByProvider, setModelsByProvider] = useState<Record<string, string[]>>({})
  const [currentModel, setCurrentModel] = useState<string>('')

  useEffect(() => {
    api.getLlmProviders()
      .then((d) => {
        setProviders(d.providers)
        setCurrentProvider(d.current_provider)
        setCurrentModel(d.current_model)
        d.providers.forEach((p) => {
          if (!p.available) return
          api.getLlmModels(p.id)
            .then((m) => {
              setModelsByProvider((prev) => ({ ...prev, [m.provider]: m.models }))
              if (p.id === d.current_provider && !m.models.includes(d.current_model)) {
                setCurrentModel(m.models[0] || '')
              }
            })
            .catch(() => {})
        })
      })
      .catch(() => setProviders([]))
  }, [])

  const activeProvider = providers.find((p) => p.id === currentProvider)
  const llmOk = activeProvider?.available ?? false

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {activeProvider && (
        <span
          className={`text-xs px-2 py-1 rounded-lg border ${
            llmOk
              ? 'bg-green-500/15 border-green-500/40 text-green-300'
              : 'bg-amber-500/15 border-amber-500/40 text-amber-300'
          }`}
          title={llmOk ? undefined : 'Provider no disponible'}
        >
          {llmOk ? `● ${activeProvider.name} lista` : `● ${activeProvider.name} no disponible`}
        </span>
      )}
      <label className="flex items-center gap-1 text-xs text-slate-400">
        Provider:
        <select
          className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-1 py-0.5 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
          value={currentProvider}
          onChange={async (e) => {
            const provider = e.target.value
            setCurrentProvider(provider)
            const models = modelsByProvider[provider] || []
            const model = models[0] || ''
            setCurrentModel(model)
            if (model) await api.setLlmModel(provider, model)
          }}
        >
          {providers.map((p) => (
            <option key={p.id} value={p.id} disabled={!p.available}>
              {p.name} {!p.available ? '(no configurado)' : ''}
            </option>
          ))}
        </select>
      </label>
      {currentProvider && (modelsByProvider[currentProvider]?.length ?? 0) > 0 && (
        <label className="flex items-center gap-1 text-xs text-slate-400">
          Modelo:
          <select
            className="bg-slate-800 border border-slate-600 text-slate-100 rounded-lg px-1 py-0.5 text-xs focus:outline-none focus:ring-2 focus:ring-purple-500"
            value={currentModel}
            onChange={async (e) => {
              const model = e.target.value
              setCurrentModel(model)
              await api.setLlmModel(currentProvider, model)
            }}
          >
            {modelsByProvider[currentProvider]?.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </label>
      )}
    </div>
  )
}
