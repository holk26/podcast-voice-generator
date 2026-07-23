import {
  Voice,
  Episode,
  CreateEpisodeRequest,
  Channel,
  CreateChannelRequest,
  ContentPlanEntry,
  CreatePlanEntryRequest,
  CrewJobStart,
  ChannelSuggestion,
} from '../types'

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

  getChannels: () => fetchJson<Channel[]>('/channels'),
  createChannel: (data: CreateChannelRequest) =>
    fetchJson<Channel>('/channels', { method: 'POST', body: JSON.stringify(data) }),
  suggestChannel: (hint?: string) =>
    fetchJson<ChannelSuggestion>('/channels/suggest', {
      method: 'POST',
      body: JSON.stringify({ hint: hint || null }),
    }),
  getChannel: (id: number) => fetchJson<Channel>(`/channels/${id}`),
  updateChannel: (id: number, data: Partial<CreateChannelRequest>) =>
    fetchJson<Channel>(`/channels/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteChannel: (id: number) => fetchVoid(`/channels/${id}`, { method: 'DELETE' }),
  activateChannel: (id: number) =>
    fetchJson<Channel>(`/channels/${id}/activate`, { method: 'POST' }),
  deactivateChannel: (id: number) =>
    fetchJson<Channel>(`/channels/${id}/deactivate`, { method: 'POST' }),

  getPlanEntries: (channelId: number) =>
    fetchJson<ContentPlanEntry[]>(`/channels/${channelId}/plan`),
  generatePlan: (channelId: number, count: number = 5) =>
    fetchJson<CrewJobStart>(`/channels/${channelId}/plan/generate?count=${count}`, { method: 'POST' }),
  createPlanEntry: (channelId: number, data: CreatePlanEntryRequest) =>
    fetchJson<ContentPlanEntry>(`/channels/${channelId}/plan`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  approvePlanEntry: (entryId: number, minutes: number = 10) =>
    fetchJson<CrewJobStart>(`/channels/plan/${entryId}/approve?minutes=${minutes}`, { method: 'POST' }),
  rejectPlanEntry: (entryId: number) =>
    fetchJson<ContentPlanEntry>(`/channels/plan/${entryId}/reject`, { method: 'POST' }),
  deletePlanEntry: (entryId: number) => fetchVoid(`/channels/plan/${entryId}`, { method: 'DELETE' }),

  getLlmStatus: () =>
    fetchJson<{ available: boolean; default_ready: boolean; error?: string }>('/llm/status'),
}
