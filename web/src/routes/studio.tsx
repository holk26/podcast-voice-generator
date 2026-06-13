import { createFileRoute } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useChannelStore } from '../stores/channelStore'
import StudioPanel from '../components/StudioPanel'

export const Route = createFileRoute('/studio')({
  component: StudioPage,
})

function StudioPage() {
  const { channels, loading, error, fetchChannels, generatePlan } = useChannelStore()

  useEffect(() => {
    fetchChannels()
  }, [fetchChannels])

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Studio</h2>
      {error && (
        <div className="bg-red-100 text-red-800 p-3 rounded mb-4">Error: {error}</div>
      )}
      <StudioPanel channels={channels} onGenerate={generatePlan} loading={loading} />
    </div>
  )
}
