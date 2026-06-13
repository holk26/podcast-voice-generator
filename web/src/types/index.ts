export interface Voice {
  id: string
  name: string
  engine: string
  language: string
  gender: string
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
  created_at: string
  updated_at: string
}

export interface ContentPlanEntry {
  id: number
  channel_id: number
  title: string
  description?: string
  scheduled_date?: string
  status: PlanEntryStatus
  episode_id?: number
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
}

export interface CreatePlanEntryRequest {
  title: string
  description?: string
  scheduled_date?: string
}
