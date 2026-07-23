import { createFileRoute } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useChannelStore } from '../stores/channelStore'
import ContentPlanList from '../components/ContentPlanList'
import CrewJobActivity from '../components/CrewJobActivity'

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

  useEffect(() => {
    fetchChannels()
    fetchPlanEntries(channelId)
  }, [fetchChannels, fetchPlanEntries, channelId])

  const channel = channels.find((c) => c.id === channelId)
  const planEntries = entries[channelId] || []

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
      {error && (
        <div className="bg-red-100 text-red-800 p-3 rounded mb-4">Error: {error}</div>
      )}
      <CrewJobActivity />
      <ContentPlanList
        entries={planEntries}
        onApprove={approveEntry}
        onReject={rejectEntry}
        onDelete={deleteEntry}
      />
    </div>
  )
}
