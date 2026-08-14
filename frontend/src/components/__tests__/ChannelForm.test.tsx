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
    fireEvent.change(screen.getByLabelText(/Nombre/i), { target: { value: 'Canal X' } })
    fireEvent.change(screen.getByLabelText(/Nicho/i), { target: { value: 'tech' } })
    fireEvent.click(screen.getByRole('button', { name: /Guardar/i }))
    expect(onSubmit).toHaveBeenCalledWith(expect.objectContaining({ name: 'Canal X', niche: 'tech', default_voice_id: 'jorge' }))
  })
})
