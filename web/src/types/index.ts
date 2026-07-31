export interface Voice {
  id: string
  name: string
  engine: string
  language: string
  gender: string
  type?: 'pretrained' | 'cloned'
  reference_path?: string | null
}

export type EpisodeStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface Episode {
  id: number
  title: string
  type: string
  source_text?: string
  voice_id: string
  status: EpisodeStatus
  audio_url?: string
  error_message?: string
  published_at?: string | null
  created_at: string
  updated_at: string
}

export interface CreateEpisodeRequest {
  title: string
  type: string
  source_text?: string
  voice_id: string
}

export type ChannelFormat = 'podcast' | 'news' | 'meditation' | 'motivation'
export type PlanEntryStatus = 'draft' | 'generated' | 'rejected'

export interface Channel {
  id: number
  name: string
  description?: string
  niche?: string
  format: ChannelFormat
  default_voice_id: string
  is_active: boolean
  autopilot: boolean
  episodes_per_week: number
  target_minutes: number
  brief?: string
  entries_total?: number
  entries_generated?: number
  published_at?: string | null
  created_at: string
  updated_at: string
}

export interface ContentPlanEntry {
  id: number
  channel_id: number
  title: string
  description?: string
  scheduled_date?: string
  season: number
  status: PlanEntryStatus
  episode_id?: number
  audio_url?: string
  episode_published_at?: string | null
  created_at: string
  updated_at: string
}

export interface CreateChannelRequest {
  name: string
  description?: string
  niche?: string
  format: ChannelFormat
  default_voice_id: string
  is_active?: boolean
  brief?: string
  autopilot?: boolean
  episodes_per_week?: number
  target_minutes?: number
}

export interface CreatePlanEntryRequest {
  title: string
  description?: string
  scheduled_date?: string
}

export interface CrewJobEvent {
  ts: number
  step: string
  message: string
  content?: string
}

export interface CrewJobStart {
  job_id: string
}

export interface ChannelSuggestion {
  name: string
  description: string
  niche: string
  format: ChannelFormat
}

export interface BookResult {
  title: string
  author: string
  book_id: string
  url: string
}

export interface BookChapter {
  index: number
  title: string
  words: number
}

export interface ActiveCrewJob {
  id: string
  kind: 'plan' | 'script' | 'season'
  channelId?: number
  events: CrewJobEvent[]
  status: 'running' | 'done' | 'error'
  error?: string
}

export interface JobSummary {
  id: string
  kind: string
  detail: string
  created_at: number
  event_count: number
}
