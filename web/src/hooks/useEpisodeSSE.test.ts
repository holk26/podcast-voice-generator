import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { useEpisodeSSE } from './useEpisodeSSE'
import type { Episode } from '../types'

class MockEventSource {
  static instances: MockEventSource[] = []
  url: string
  onmessage: ((event: MessageEvent) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  readyState = 0

  constructor(url: string) {
    this.url = url
    MockEventSource.instances.push(this)
  }

  close() {
    this.readyState = 2
    MockEventSource.instances = MockEventSource.instances.filter((i) => i !== this)
  }

  emit(data: string) {
    this.onmessage?.call(this, { data } as MessageEvent)
  }

  error() {
    this.onerror?.call(this, new Event('error'))
  }

  static reset() {
    MockEventSource.instances = []
  }
}

describe('useEpisodeSSE', () => {
  beforeEach(() => {
    MockEventSource.reset()
    global.EventSource = MockEventSource as unknown as typeof EventSource
  })

  it('opens one EventSource per pending/running episode', () => {
    const updateEpisode = vi.fn()
    const episodes: Episode[] = [
      { id: 1, title: 'A', type: 'podcast', voice_id: 'v1', status: 'pending', created_at: '', updated_at: '' },
      { id: 2, title: 'B', type: 'podcast', voice_id: 'v1', status: 'running', created_at: '', updated_at: '' },
      { id: 3, title: 'C', type: 'podcast', voice_id: 'v1', status: 'completed', created_at: '', updated_at: '' },
    ]

    renderHook(() => useEpisodeSSE(episodes, updateEpisode))

    expect(MockEventSource.instances.length).toBe(2)
    expect(MockEventSource.instances.map((i) => i.url)).toContain('/api/episodes/1/events')
    expect(MockEventSource.instances.map((i) => i.url)).toContain('/api/episodes/2/events')
  })

  it('updates episode when SSE message arrives', () => {
    const updateEpisode = vi.fn()
    const episodes: Episode[] = [
      { id: 1, title: 'A', type: 'podcast', voice_id: 'v1', status: 'pending', created_at: '', updated_at: '' },
    ]

    renderHook(() => useEpisodeSSE(episodes, updateEpisode))
    const [es] = MockEventSource.instances
    es.emit(JSON.stringify({ status: 'running', audio_url: '/out/1.mp3' }))

    expect(updateEpisode).toHaveBeenCalledTimes(1)
    expect(updateEpisode).toHaveBeenCalledWith(1, {
      status: 'running',
      audio_url: '/out/1.mp3',
    })
  })

  it('does not open duplicate connections on re-renders', () => {
    const updateEpisode = vi.fn()
    const episodes: Episode[] = [
      { id: 1, title: 'A', type: 'podcast', voice_id: 'v1', status: 'pending', created_at: '', updated_at: '' },
    ]

    const { rerender } = renderHook(({ eps }) => useEpisodeSSE(eps, updateEpisode), {
      initialProps: { eps: episodes },
    })
    expect(MockEventSource.instances.length).toBe(1)

    rerender({
      eps: [
        { id: 1, title: 'A', type: 'podcast', voice_id: 'v1', status: 'pending', created_at: '', updated_at: '' },
      ],
    })
    expect(MockEventSource.instances.length).toBe(1)
  })

  it('does not close the connection on transient SSE errors', () => {
    const updateEpisode = vi.fn()
    const episodes: Episode[] = [
      { id: 1, title: 'A', type: 'podcast', voice_id: 'v1', status: 'pending', created_at: '', updated_at: '' },
    ]

    renderHook(() => useEpisodeSSE(episodes, updateEpisode))
    const [es] = MockEventSource.instances
    es.error()

    expect(MockEventSource.instances.length).toBe(1)
  })

  it('gives up and closes the connection after repeated SSE errors', () => {
    const updateEpisode = vi.fn()
    const episodes: Episode[] = [
      { id: 1, title: 'A', type: 'podcast', voice_id: 'v1', status: 'pending', created_at: '', updated_at: '' },
    ]

    renderHook(() => useEpisodeSSE(episodes, updateEpisode))
    const [es] = MockEventSource.instances
    for (let i = 0; i < 6; i++) {
      es.error()
    }

    expect(MockEventSource.instances.length).toBe(0)
    expect(updateEpisode).toHaveBeenLastCalledWith(1, {
      status: 'failed',
      error_message: 'Se perdió la conexión en tiempo real tras varios intentos.',
    })
  })

  it('closes the connection immediately when a terminal status arrives', () => {
    const updateEpisode = vi.fn()
    const episodes: Episode[] = [
      { id: 1, title: 'A', type: 'podcast', voice_id: 'v1', status: 'running', created_at: '', updated_at: '' },
    ]

    renderHook(() => useEpisodeSSE(episodes, updateEpisode))
    const [es] = MockEventSource.instances
    es.emit(JSON.stringify({ status: 'completed', audio_url: '/out/1.mp3' }))

    expect(MockEventSource.instances.length).toBe(0)
    expect(updateEpisode).toHaveBeenLastCalledWith(1, {
      status: 'completed',
      audio_url: '/out/1.mp3',
    })
  })

  it('resets the error counter after a successful message', () => {
    const updateEpisode = vi.fn()
    const episodes: Episode[] = [
      { id: 1, title: 'A', type: 'podcast', voice_id: 'v1', status: 'pending', created_at: '', updated_at: '' },
    ]

    renderHook(() => useEpisodeSSE(episodes, updateEpisode))
    const [es] = MockEventSource.instances

    // Four transient errors should not close the connection.
    for (let i = 0; i < 4; i++) {
      es.error()
    }
    // A successful message resets the counter.
    es.emit(JSON.stringify({ status: 'running' }))
    // Four more transient errors should still not close it.
    for (let i = 0; i < 4; i++) {
      es.error()
    }

    expect(MockEventSource.instances.length).toBe(1)
  })

  it('closes connection when episode status is no longer pending/running', () => {
    const updateEpisode = vi.fn()
    const pending: Episode[] = [
      { id: 1, title: 'A', type: 'podcast', voice_id: 'v1', status: 'pending', created_at: '', updated_at: '' },
    ]

    const { rerender } = renderHook(({ eps }) => useEpisodeSSE(eps, updateEpisode), {
      initialProps: { eps: pending },
    })

    expect(MockEventSource.instances.length).toBe(1)

    const completed: Episode[] = [
      { id: 1, title: 'A', type: 'podcast', voice_id: 'v1', status: 'completed', created_at: '', updated_at: '' },
    ]
    rerender({ eps: completed })

    expect(MockEventSource.instances.length).toBe(0)
  })

  it('closes all connections on unmount', () => {
    const updateEpisode = vi.fn()
    const episodes: Episode[] = [
      { id: 1, title: 'A', type: 'podcast', voice_id: 'v1', status: 'pending', created_at: '', updated_at: '' },
      { id: 2, title: 'B', type: 'podcast', voice_id: 'v1', status: 'running', created_at: '', updated_at: '' },
    ]

    const { unmount } = renderHook(() => useEpisodeSSE(episodes, updateEpisode))
    expect(MockEventSource.instances.length).toBe(2)

    unmount()
    expect(MockEventSource.instances.length).toBe(0)
  })

  it('survives malformed SSE payloads without crashing', () => {
    const updateEpisode = vi.fn()
    const episodes: Episode[] = [
      { id: 1, title: 'A', type: 'podcast', voice_id: 'v1', status: 'pending', created_at: '', updated_at: '' },
    ]

    renderHook(() => useEpisodeSSE(episodes, updateEpisode))
    const [es] = MockEventSource.instances

    expect(() => es.emit('not json')).not.toThrow()
    expect(updateEpisode).not.toHaveBeenCalled()
  })
})
