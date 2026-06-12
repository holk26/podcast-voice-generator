export interface Voice {
  id: string
  name: string
  engine: string
  language: string
  gender: string
}

export interface Episode {
  id: number
  title: string
  type: string
  source_text?: string
  voice_id: string
  status: string
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
