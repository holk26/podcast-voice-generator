import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import GenerateScriptWizard from '../GenerateScriptWizard'
import { api } from '../../api/client'
import { Channel } from '../../types'

vi.mock('../../api/client', () => ({
  api: {
    startScriptJob: vi.fn(),
    createFromText: vi.fn(),
  },
  sseUrl: (p: string) => p,
}))

vi.mock('@tanstack/react-router', () => ({
  useNavigate: () => vi.fn(),
}))

class MockEventSource {
  static instances: MockEventSource[] = []
  url: string
  onmessage: ((e: MessageEvent) => void) | null = null
  onerror: (() => void) | null = null
  closed = false
  constructor(url: string) { this.url = url; MockEventSource.instances.push(this) }
  close() { this.closed = true }
  emit(data: object) { this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent) }
}

const channel = { id: 3, name: 'Crimenes', format: 'podcast' } as unknown as Channel

describe('GenerateScriptWizard', () => {
  beforeEach(() => {
    MockEventSource.instances = []
    ;(globalThis as unknown as { EventSource: unknown }).EventSource = MockEventSource
    vi.clearAllMocks()
  })

  it('fuente → progreso → edición → crear episodio', async () => {
    ;(api.startScriptJob as ReturnType<typeof vi.fn>).mockResolvedValue({ job_id: 'job1' })
    ;(api.createFromText as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 99 })

    render(<GenerateScriptWizard channel={channel} onClose={() => {}} />)

    fireEvent.change(screen.getByPlaceholderText(/Pega aquí/), { target: { value: 'Material' } })
    fireEvent.click(screen.getByText('Lanzar congreso 🎬'))

    await waitFor(() => expect(api.startScriptJob).toHaveBeenCalledWith(3, expect.objectContaining({ text: 'Material' })))
    expect(screen.getByText("trabajando…")).toBeInTheDocument()

    const es = MockEventSource.instances[0]
    es.emit({ step: 'research', message: 'Investigando…' })
    es.emit({ step: '__status__', status: 'done', result: { script_text: 'Guion final', title: 'T', word_count: 2 } })

    await waitFor(() => expect(screen.getByDisplayValue('Guion final')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Crear episodio'))

    await waitFor(() => expect(api.createFromText).toHaveBeenCalledWith(3, 'Guion final', 'T'))
  })

  it('job con error muestra mensaje', async () => {
    ;(api.startScriptJob as ReturnType<typeof vi.fn>).mockResolvedValue({ job_id: 'job2' })
    render(<GenerateScriptWizard channel={channel} onClose={() => {}} />)
    fireEvent.change(screen.getByPlaceholderText(/Pega aquí/), { target: { value: 'x' } })
    fireEvent.click(screen.getByText('Lanzar congreso 🎬'))
    await waitFor(() => expect(MockEventSource.instances.length).toBe(1))
    MockEventSource.instances[0].emit({ step: '__status__', status: 'error', error: 'LLM caído' })
    await waitFor(() => expect(screen.getByText(/LLM caído/)).toBeInTheDocument())
  })
})
