import { createFileRoute } from '@tanstack/react-router'
import { useEffect, useState } from 'react'
import { useChannelStore } from '../stores/channelStore'
import ContentPlanList from '../components/ContentPlanList'
import CongressTable from '../components/CongressTable'

export const Route = createFileRoute('/channels/$id/plan')({
  component: ChannelPlanPage,
})

function ChannelPlanPage() {
  const { id } = Route.useParams()
  const channelId = Number(id)
  const {
    channels,
    entries,
    loading,
    error,
    fetchChannels,
    fetchPlanEntries,
    generatePlan,
    approveEntry,
    rejectEntry,
    deleteEntry,
  } = useChannelStore()
  const [seasonFilter, setSeasonFilter] = useState<number | null>(null) // null = todas

  useEffect(() => {
    fetchChannels()
    fetchPlanEntries(channelId)
  }, [fetchChannels, fetchPlanEntries, channelId])

  const channel = channels.find((c) => c.id === channelId)
  const planEntries = entries[channelId] || []
  const total = channel?.entries_total ?? planEntries.length
  const generated = channel?.entries_generated ?? planEntries.filter((e) => e.status === 'generated').length
  const pct = total > 0 ? Math.round((generated / total) * 100) : 0

  const seasons = [...new Set(planEntries.map((e) => e.season ?? 1))].sort((a, b) => a - b)
  const filtered = seasonFilter === null
    ? planEntries
    : planEntries.filter((e) => (e.season ?? 1) === seasonFilter)

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold">Plan editorial: {channel?.name}</h2>
        <button
          type="button"
          onClick={() => generatePlan(channelId)}
          className="bg-purple-600 text-white px-4 py-2 rounded"
          disabled={loading}
        >
          Generar con IA
        </button>
      </div>
      {total > 0 && (
        <div className="mb-4">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>{generated}/{total} capítulos generados</span>
            <span>{pct}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded h-2">
            <div className="bg-green-500 h-2 rounded" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}
      {seasons.length > 1 && (
        <div className="flex gap-2 mb-4">
          <button
            type="button"
            onClick={() => setSeasonFilter(null)}
            className={`px-3 py-1 rounded text-sm ${
              seasonFilter === null ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-700'
            }`}
          >
            Todas
          </button>
          {seasons.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setSeasonFilter(s)}
              className={`px-3 py-1 rounded text-sm ${
                seasonFilter === s ? 'bg-purple-600 text-white' : 'bg-gray-100 text-gray-700'
              }`}
            >
              Temporada {s}
            </button>
          ))}
        </div>
      )}
      {error && (
        <div className="bg-red-100 text-red-800 p-3 rounded mb-4">Error: {error}</div>
      )}
      <CongressTable />
      <ContentPlanList
        entries={filtered}
        onApprove={approveEntry}
        onReject={rejectEntry}
        onDelete={deleteEntry}
      />
    </div>
  )
}
