import { createFileRoute, Link } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useChannelStore } from '../stores/channelStore'
import ChannelCard from '../components/ChannelCard'

export const Route = createFileRoute('/channels/')({
  component: ChannelsPage,
})

function ChannelsPage() {
  const { channels, loading, error, fetchChannels, deleteChannel } = useChannelStore()

  useEffect(() => {
    fetchChannels()
  }, [fetchChannels])

  if (loading) return <div className="text-slate-400">Cargando canales...</div>

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-2xl font-bold tracking-tight">Canales</h2>
        <Link to="/channels/new" className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-500 transition-colors">
          Nuevo canal
        </Link>
      </div>
      {error && (
        <div className="bg-red-500/10 border border-red-500/40 text-red-300 p-3 rounded-lg mb-4">Error: {error}</div>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        {channels.map((channel) => (
          <ChannelCard key={channel.id} channel={channel} onDelete={deleteChannel} />
        ))}
      </div>
    </div>
  )
}
