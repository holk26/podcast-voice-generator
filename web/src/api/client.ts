import { Voice, Episode, CreateEpisodeRequest } from '../types'

const API_BASE = '/api'

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
  return response.json()
}

async function fetchVoid(url: string, options?: RequestInit): Promise<void> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options?.headers ?? {}),
    },
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`)
  }
}

export const api = {
  getVoices: () => fetchJson<Voice[]>('/voices'),
  previewTts: (text: string, voiceId: string) =>
    fetchJson<{ audio_url: string }>('/tts/preview', {
      method: 'POST',
      body: JSON.stringify({ text, voice_id: voiceId }),
    }),
  getEpisodes: () => fetchJson<Episode[]>('/episodes'),
  getEpisode: (id: number) => fetchJson<Episode>(`/episodes/${id}`),
  createEpisode: (data: CreateEpisodeRequest) =>
    fetchJson<Episode>('/episodes', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  deleteEpisode: (id: number) => fetchVoid(`/episodes/${id}`, { method: 'DELETE' }),
}
