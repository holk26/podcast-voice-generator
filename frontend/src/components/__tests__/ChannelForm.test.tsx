import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import ChannelForm from '../ChannelForm'

const VOICES = [
  { id: 'jorge', name: 'Jorge', engine: 'edge', language: 'es', gender: 'male' },
]

describe('ChannelForm', () => {
  it('submits channel data', () => {
    const onSubmit = vi.fn()
    render(<ChannelForm voices={VOICES} onSubmit={onSubmit} onCancel={vi.fn()} />)
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Canal X' } })
    fireEvent.change(screen.getByLabelText(/Nicho/i), { target: { value: 'tech' } })
    fireEvent.click(screen.getByRole('button', { name: /Guardar/i }))
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ name: 'Canal X', niche: 'tech', default_voice_id: 'jorge' }))
  })

  it('al elegir 2 voces envía num_speakers y speaker_voices', () => {
    const onSubmit = vi.fn()
    render(<ChannelForm voices={VOICES} onSubmit={onSubmit} onCancel={vi.fn()} />)
    fireEvent.change(screen.getByLabelText(/Número de voces/i), { target: { value: '2' } })
    expect(screen.getByLabelText(/Voz de Narrador/i)).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Canal Y' } })
    fireEvent.click(screen.getByRole('button', { name: /Guardar/i }))
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      num_speakers: 2,
      speaker_voices: { Narrador: 'jorge', Invitado: 'jorge' },
    }))
  })

  it('con 1 voz envía speaker_voices null', () => {
    const onSubmit = vi.fn()
    render(<ChannelForm voices={VOICES} onSubmit={onSubmit} onCancel={vi.fn()} />)
    fireEvent.change(screen.getByLabelText('Nombre'), { target: { value: 'Canal Z' } })
    fireEvent.click(screen.getByRole('button', { name: /Guardar/i }))
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({
      num_speakers: 1,
      speaker_voices: null,
    }))
  })
})
