import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useChannelStore } from '../stores/channelStore'
import ChannelForm from '../components/ChannelForm'
import { CreateChannelRequest } from '../types'

export const Route = createFileRoute('/channels/new')({
  component: NewChannelPage,
})

function NewChannelPage() {
  const navigate = useNavigate()
  const { createChannel } = useChannelStore()

  const handleSubmit = async (data: CreateChannelRequest) => {
    await createChannel(data)
    navigate({ to: '/channels' })
  }

  return (
    <div>
      <h2 className="text-2xl font-bold mb-4">Nuevo canal</h2>
      <ChannelForm
        onSubmit={handleSubmit}
        onCancel={() => navigate({ to: '/channels' })}
      />
    </div>
  )
}
