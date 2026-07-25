import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useEffect } from 'react'
import { useChannelStore } from '../stores/channelStore'
import { useVoiceStore } from '../stores/voiceStore'
import ChannelForm from '../components/ChannelForm'
import { CreateChannelRequest } from '../types'

export const Route = createFileRoute('/channels/$id/edit')({
  component: EditChannelPage,
})

function EditChannelPage() {
  const { id } = Route.useParams()
  const channelId = Number(id)
  const navigate = useNavigate()
  const { channels, updateChannel, fetchChannels } = useChannelStore()
  const { voices, fetchVoices } = useVoiceStore()

  useEffect(() => {
    fetchChannels()
    fetchVoices()
  }, [fetchChannels, fetchVoices])

  const channel = channels.find((c) => c.id === channelId)

  const handleSubmit = async (data: CreateChannelRequest) => {
    await updateChannel(channelId, data)
    navigate({ to: '/channels' })
  }

  if (!channel) {
    return <div className="text-slate-400">Cargando canal...</div>
  }

  return (
    <div>
      <h2 className="text-2xl font-bold tracking-tight mb-4">Editar canal: {channel.name}</h2>
      <ChannelForm
        voices={voices}
        initial={channel}
        onSubmit={handleSubmit}
        onCancel={() => navigate({ to: '/channels' })}
      />
    </div>
  )
}
