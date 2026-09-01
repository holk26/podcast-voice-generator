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
  BookResult,
  BookChapter,
  JobSummary,
  LoginRequest,
  LoginResponse,
  LlmProvidersResponse,
  LlmModelsResponse,
  LlmSettingsRequest,
} from '../types'
import { getAuthToken } from './auth'

export const API_BASE = import.meta.env.VITE_API_URL || '/api'

export function sseUrl(path: string): string {
  const token = getAuthToken()
  const separator = path.includes('?') ? '&' : '?'
  return `${API_BASE}${path}${token ? `${separator}token=${encodeURIComponent(token)}` : ''}`
}

async function parseError(response: Response): Promise<Error> {
  try {
    const body = await response.json()
    if (body?.detail) {
      const detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
      return new Error(`HTTP ${response.status}: ${detail}`)
    }
  } catch {
    // cuerpo no JSON
  }
  return new Error(`HTTP ${response.status}: ${response.statusText}`)
}

function buildHeaders(options?: RequestInit): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options?.headers as Record<string, string> ?? {}),
  }
  const token = getAuthToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  return headers
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: buildHeaders(options),
  })
  if (!response.ok) {
    throw await parseError(response)
  }
  return response.json()
}

async function fetchVoid(url: string, options?: RequestInit): Promise<void> {
  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers: buildHeaders(options),
  })
  if (!response.ok) {
    throw await parseError(response)
  }
}

async function fetchFormData<T>(url: string, formData: FormData): Promise<T> {
  const headers: Record<string, string> = {}
  const token = getAuthToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const response = await fetch(`${API_BASE}${url}`, {
    method: 'POST',
    headers,
    body: formData,
  })
  if (!response.ok) {
    throw await parseError(response)
  }
  return response.json()
}

export const api = {
  login: (username: string, password: string) =>
    fetchJson<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password } as LoginRequest),
    }),

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
  updateEpisode: (id: number, data: Partial<CreateEpisodeRequest>) =>
    fetchJson<Episode>(`/episodes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  retryEpisode: (id: number) =>
    fetchJson<Episode>(`/episodes/${id}/retry`, { method: 'POST' }),
  publishEpisode: (id: number) =>
    fetchJson<Episode>(`/episodes/${id}/publish`, { method: 'POST' }),
  unpublishEpisode: (id: number) =>
    fetchJson<Episode>(`/episodes/${id}/unpublish`, { method: 'POST' }),

  getChannels: () => fetchJson<Channel[]>('/channels'),
  createChannel: (data: CreateChannelRequest) =>
    fetchJson<Channel>('/channels', { method: 'POST', body: JSON.stringify(data) }),
  suggestChannel: (hint?: string) =>
    fetchJson<ChannelSuggestion>('/channels/suggest', {
      method: 'POST',
      body: JSON.stringify({ hint: hint || null }),
    }),
  improveChannelPrompt: (id: number) =>
    fetchJson<{ brief: string }>(`/channels/${id}/improve-prompt`, { method: 'POST' }),
  getChannel: (id: number) => fetchJson<Channel>(`/channels/${id}`),
  updateChannel: (id: number, data: Partial<CreateChannelRequest>) =>
    fetchJson<Channel>(`/channels/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteChannel: (id: number) => fetchVoid(`/channels/${id}`, { method: 'DELETE' }),
  activateChannel: (id: number) =>
    fetchJson<Channel>(`/channels/${id}/activate`, { method: 'POST' }),
  deactivateChannel: (id: number) =>
    fetchJson<Channel>(`/channels/${id}/deactivate`, { method: 'POST' }),
  publishChannel: (id: number) =>
    fetchJson<Channel>(`/channels/${id}/publish`, { method: 'POST' }),
  unpublishChannel: (id: number) =>
    fetchJson<Channel>(`/channels/${id}/unpublish`, { method: 'POST' }),

  getPlanEntries: (channelId: number) =>
    fetchJson<ContentPlanEntry[]>(`/channels/${channelId}/plan`),
  generatePlan: (channelId: number, count: number = 5) =>
    fetchJson<CrewJobStart>(`/channels/${channelId}/plan/generate?count=${count}`, { method: 'POST' }),
  generateSeason: (channelId: number, weeks: number = 4) =>
    fetchJson<CrewJobStart>(`/channels/${channelId}/season?weeks=${weeks}`, { method: 'POST' }),
  createPlanEntry: (channelId: number, data: CreatePlanEntryRequest) =>
    fetchJson<ContentPlanEntry>(`/channels/${channelId}/plan`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  approvePlanEntry: (entryId: number, minutes: number = 10) =>
    fetchJson<CrewJobStart>(`/channels/plan/${entryId}/approve?minutes=${minutes}`, { method: 'POST' }),
  updatePlanEntry: (entryId: number, data: CreatePlanEntryRequest) =>
    fetchJson<ContentPlanEntry>(`/channels/plan/${entryId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  rejectPlanEntry: (entryId: number) =>
    fetchJson<ContentPlanEntry>(`/channels/plan/${entryId}/reject`, { method: 'POST' }),
  deletePlanEntry: (entryId: number) => fetchVoid(`/channels/plan/${entryId}`, { method: 'DELETE' }),

  uploadScript: (channelId: number, file: File, title?: string) => {
    const formData = new FormData()
    formData.append('script', file)
    if (title) {
      formData.append('title', title)
    }
    return fetchFormData<Episode>(`/channels/${channelId}/upload-script`, formData)
  },

  createFromText: (channelId: number, sourceText: string, title?: string) =>
    fetchJson<Episode>(`/channels/${channelId}/create-from-text`, {
      method: 'POST',
      body: JSON.stringify({ source_text: sourceText, title }),
    }),

  searchBooks: (q: string) =>
    fetchJson<BookResult[]>(`/books/search?q=${encodeURIComponent(q)}`),
  getBookChapters: (bookId: string) =>
    fetchJson<BookChapter[]>(`/books/${bookId}/chapters`),
  convertBookChapter: (bookId: string, chapterIndex: number, voiceId: string) =>
    fetchJson<CrewJobStart>(`/books/${bookId}/to-episode`, {
      method: 'POST',
      body: JSON.stringify({ chapter_index: chapterIndex, voice_id: voiceId }),
    }),

  getJobs: () => fetchJson<JobSummary[]>('/jobs'),

  getLlmStatus: () =>
    fetchJson<{ available: boolean; default_ready: boolean; error?: string }>('/llm/status'),
  getLlmProviders: () =>
    fetchJson<LlmProvidersResponse>('/llm/providers'),
  getLlmModels: (provider?: string) =>
    fetchJson<LlmModelsResponse>(`/llm/models${provider ? `?provider=${encodeURIComponent(provider)}` : ''}`),
  setLlmModel: (provider: string, model: string) =>
    fetchJson<{ current_provider: string; current_model: string }>('/llm/model', {
      method: 'POST',
      body: JSON.stringify({ provider, model } as LlmSettingsRequest),
    }),
}
