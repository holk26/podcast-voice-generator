import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

const generatePlanMock = vi.fn()

vi.mock('../../api/client', () => ({
  api: {
    generatePlan: (...args: unknown[]) => generatePlanMock(...args),
    getPlanEntries: vi.fn().mockResolvedValue([]),
  },
  sseUrl: (path: string) => `http://test${path}`,
}))

class FakeEventSource {
  static instances: FakeEventSource[] = []

  onmessage: ((event: MessageEvent<string>) => void) | null = null
  onerror: (() => void) | null = null
  url: string
  closed = false

  constructor(url: string) {
    this.url = url
    FakeEventSource.instances.push(this)
  }

  close() {
    this.closed = true
  }

  emit(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent<string>)
  }

  fail() {
    this.onerror?.()
  }
}

import { useChannelStore } from '../channelStore'

describe('channelStore', () => {
  beforeEach(() => {
    FakeEventSource.instances = []
    generatePlanMock.mockReset()
    generatePlanMock.mockResolvedValue({ job_id: 'abc123' })
    vi.stubGlobal('EventSource', FakeEventSource)
    vi.useFakeTimers()
    useChannelStore.setState({ activeJob: null, error: null, loading: false })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('has empty channels by default', () => {
    const state = useChannelStore.getState()
    expect(state.channels).toEqual([])
    expect(state.loading).toBe(false)
  })

  it('reconecta ante errores del SSE y reconstruye los eventos (replay)', async () => {
    const promise = useChannelStore.getState().generatePlan(1, 5)
    await promise
    expect(FakeEventSource.instances).toHaveLength(1)

    const first = FakeEventSource.instances[0]
    first.emit({ step: 'research', message: 'investigando' })
    expect(useChannelStore.getState().activeJob?.events).toHaveLength(1)

    // Error de conexión: no debe rendirse, debe programar una reconexión.
    first.fail()
    expect(useChannelStore.getState().activeJob?.status).toBe('running')
    expect(useChannelStore.getState().error).toContain('Reconectando')
    expect(FakeEventSource.instances).toHaveLength(1)

    await vi.advanceTimersByTimeAsync(2000)
    expect(FakeEventSource.instances).toHaveLength(2)

    // El servidor re-emite todos los eventos desde cero: la lista se reconstruye.
    const second = FakeEventSource.instances[1]
    second.emit({ step: 'research', message: 'investigando' })
    second.emit({ step: 'writing', message: 'escribiendo' })
    const events = useChannelStore.getState().activeJob?.events ?? []
    expect(events).toHaveLength(2)
    expect(events.map((e) => e.step)).toEqual(['research', 'writing'])

    second.emit({ step: '__status__', status: 'done', result: {} })
    // fetchPlanEntries se dispara al completar: dejar que sus microtasks terminen.
    await vi.advanceTimersByTimeAsync(0)
    await vi.advanceTimersByTimeAsync(0)
    const final = useChannelStore.getState()
    expect(final.activeJob?.status).toBe('done')
    expect(final.loading).toBe(false)
    expect(final.error).toBeNull()
  })

  it('se rinde tras superar el máximo de intentos de reconexión', async () => {
    const promise = useChannelStore.getState().generatePlan(1, 5)
    await promise

    for (let attempt = 1; attempt <= 9; attempt += 1) {
      const current = FakeEventSource.instances[FakeEventSource.instances.length - 1]
      current.fail()
      if (attempt <= 8) {
        await vi.advanceTimersByTimeAsync(10000)
      }
    }

    const state = useChannelStore.getState()
    expect(state.activeJob?.status).toBe('error')
    expect(state.error).toBe('Se perdió la conexión en tiempo real.')
  })
})
