import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import EpisodeCard from './EpisodeCard'
import type { Episode } from '../types'

vi.mock('./AudioPlayer', () => ({
  default: ({ src }: { src: string }) => <audio data-testid="audio-player" src={src} />,
}))

function makeEpisode(overrides: Partial<Episode> = {}): Episode {
  return {
    id: 1,
    title: 'Test Episode',
    type: 'podcast',
    voice_id: 'v1',
    status: 'pending',
    created_at: '',
    updated_at: '',
    ...overrides,
  }
}

describe('EpisodeCard', () => {
  it('renders episode title and status', () => {
    render(<EpisodeCard episode={makeEpisode()} onDelete={vi.fn()} />)
    expect(screen.getByText('Test Episode')).toBeInTheDocument()
    expect(screen.getByText('pending')).toBeInTheDocument()
  })

  it('renders error message when present', () => {
    render(<EpisodeCard episode={makeEpisode({ error_message: 'Something failed' })} onDelete={vi.fn()} />)
    expect(screen.getByText('Something failed')).toBeInTheDocument()
  })

  it('renders audio player when audio_url is present', () => {
    render(<EpisodeCard episode={makeEpisode({ status: 'completed', audio_url: '/out/1.mp3' })} onDelete={vi.fn()} />)
    expect(screen.getByTestId('audio-player')).toHaveAttribute('src', '/out/1.mp3')
  })

  it('calls onDelete when delete button is clicked', () => {
    const onDelete = vi.fn()
    render(<EpisodeCard episode={makeEpisode()} onDelete={onDelete} />)
    fireEvent.click(screen.getByRole('button', { name: /Eliminar episodio Test Episode/i }))
    expect(onDelete).toHaveBeenCalledWith(1)
  })

  it('applies highlight ring when highlighted', () => {
    const { container } = render(
      <EpisodeCard episode={makeEpisode()} onDelete={vi.fn()} highlighted />
    )
    expect(container.firstChild).toHaveClass('ring-2')
  })
})
