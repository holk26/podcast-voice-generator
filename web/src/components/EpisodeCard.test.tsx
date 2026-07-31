import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import EpisodeCard from './EpisodeCard'
import type { Episode } from '../types'

vi.mock('../stores/episodeStore', () => ({
  useEpisodeStore: (sel: any) =>
    sel({
      publishEpisode: vi.fn(),
      unpublishEpisode: vi.fn(),
    }),
}))

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
    render(<EpisodeCard episode={makeEpisode()} onDelete={vi.fn()} onRetry={vi.fn()} />)
    expect(screen.getByText('Test Episode')).toBeInTheDocument()
    expect(screen.getByText('Pendiente')).toBeInTheDocument()
  })

  it('renders error message when present', () => {
    render(<EpisodeCard episode={makeEpisode({ error_message: 'Something failed' })} onDelete={vi.fn()} onRetry={vi.fn()} />)
    expect(screen.getByText('Something failed')).toBeInTheDocument()
  })

  it('renders audio player when audio_url is present', () => {
    render(<EpisodeCard episode={makeEpisode({ status: 'completed', audio_url: '/out/1.mp3' })} onDelete={vi.fn()} onRetry={vi.fn()} />)
    expect(screen.getByTestId('audio-player')).toHaveAttribute('src', '/out/1.mp3')
  })

  it('calls onDelete when delete button is clicked', () => {
    const onDelete = vi.fn()
    render(<EpisodeCard episode={makeEpisode()} onDelete={onDelete} onRetry={vi.fn()} />)
    fireEvent.click(screen.getByRole('button', { name: /Eliminar episodio Test Episode/i }))
    expect(onDelete).toHaveBeenCalledWith(1)
  })

  it('applies highlight ring when highlighted', () => {
    const { container } = render(
      <EpisodeCard episode={makeEpisode()} onDelete={vi.fn()} onRetry={vi.fn()} highlighted />
    )
    expect(container.firstChild).toHaveClass('ring-2')
  })

  it('shows publish button when completed and not published', () => {
    render(<EpisodeCard episode={makeEpisode({ status: 'completed' })} onDelete={vi.fn()} onRetry={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Marcar publicado/i })).toBeInTheDocument()
  })

  it('shows published badge and unpublish button when published', () => {
    render(
      <EpisodeCard
        episode={makeEpisode({ status: 'completed', published_at: '2026-07-30T10:00:00' })}
        onDelete={vi.fn()}
        onRetry={vi.fn()}
      />
    )
    expect(screen.getByText(/Publicado/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Desmarcar/i })).toBeInTheDocument()
  })

  it('does not show publish button when not completed', () => {
    render(<EpisodeCard episode={makeEpisode({ status: 'pending' })} onDelete={vi.fn()} onRetry={vi.fn()} />)
    expect(screen.queryByRole('button', { name: /Marcar publicado/i })).not.toBeInTheDocument()
  })
})
