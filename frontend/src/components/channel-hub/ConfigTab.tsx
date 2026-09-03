import { useEffect } from 'react'
import { useChannelStore } from '../../stores/channelStore'
import { useVoiceStore } from '../../stores/voiceStore'
import { useAppStore } from '../../stores/appStore'
import ChannelForm from '../ChannelForm'
import { Channel, CreateChannelRequest } from '../../types'

export default function ConfigTab({ channel }: { channel: Channel }) {
  const { updateChannel } = useChannelStore()
  const { voices, fetchVoices } = useVoiceStore()
  const pushToast = useAppStore((s) => s.pushToast)

  useEffect(() => {
    fetchVoices()
  }, [fetchVoices])

  const handleSubmit = async (data: CreateChannelRequest) => {
    await updateChannel(channel.id, data)
    pushToast('Canal actualizado', 'success')
  }

  return (
    <div className="max-w-2xl">
      <p className="text-sm text-slate-400 mb-4">
        Cambios con guardado explícito. El formato y la voz se usan al generar guiones con IA.
      </p>
      <ChannelForm voices={voices} initial={channel} onSubmit={handleSubmit} onCancel={() => {}} />
    </div>
  )
}
