import { create } from 'zustand'
import { Episode, CreateEpisodeRequest } from '../types'
import { api } from '../api/client'
import { formatError } from '../utils/error'

interface EpisodeState {
  episodes: Episode[]
  loading: boolean
  error: string | null
  fetchEpisodes: (channelId?: number) => Promise<void>
  createEpisode: (data: CreateEpisodeRequest) => Promise<Episode>
  deleteEpisode: (id: number) => Promise<void>
  updateEpisode: (id: number, data: Partial<CreateEpisodeRequest>) => Promise<Episode>
  retryEpisode: (id: number) => Promise<Episode>
  publishEpisode: (id: number) => Promise<void>
  unpublishEpisode: (id: number) => Promise<void>
  applyEpisodeUpdate: (id: number, data: Partial<Episode>) => void
}

export const useEpisodeStore = create<EpisodeState>((set) => ({
  episodes: [],
  loading: false,
  error: null,
  fetchEpisodes: async (channelId?: number) => {
    set({ loading: true, error: null })
    try {
      const episodes = await api.getEpisodes(channelId)
      set({ episodes, loading: false })
    } catch (error) {
      set({ error: formatError(error), loading: false })
    }
  },
  createEpisode: async (data) => {
    set({ error: null })
    try {
      const episode = await api.createEpisode(data)
      set((state) => ({ episodes: [episode, ...state.episodes] }))
      return episode
    } catch (error) {
      set({ error: formatError(error) })
      throw error
    }
  },
  deleteEpisode: async (id) => {
    set({ error: null })
    try {
      await api.deleteEpisode(id)
      set((state) => ({
        episodes: state.episodes.filter((e) => e.id !== id),
      }))
    } catch (error) {
      set({ error: formatError(error) })
      throw error
    }
  },
  updateEpisode: async (id, data) => {
    set({ error: null })
    try {
      // Fetch current episode to merge all fields (PUT replaces the whole object)
      const current = await api.getEpisode(id)
      const merged = { title: current.title, type: current.type, voice_id: current.voice_id, source_text: current.source_text, ...data }
      const episode = await api.updateEpisode(id, merged)
      set((state) => ({
        episodes: state.episodes.map((e) => (e.id === id ? episode : e)),
      }))
      return episode
    } catch (error) {
      set({ error: formatError(error) })
      throw error
    }
  },
  retryEpisode: async (id) => {
    set({ error: null })
    try {
      const episode = await api.retryEpisode(id)
      set((state) => ({
        episodes: state.episodes.map((e) =>
          e.id === id ? episode : e
        ),
      }))
      return episode
    } catch (error) {
      set({ error: formatError(error) })
      throw error
    }
  },
  publishEpisode: async (id) => {
    set({ error: null })
    try {
      const episode = await api.publishEpisode(id)
      set((state) => ({
        episodes: state.episodes.map((e) => (e.id === id ? episode : e)),
      }))
    } catch (error) {
      set({ error: formatError(error) })
      throw error
    }
  },
  unpublishEpisode: async (id) => {
    set({ error: null })
    try {
      const episode = await api.unpublishEpisode(id)
      set((state) => ({
        episodes: state.episodes.map((e) => (e.id === id ? episode : e)),
      }))
    } catch (error) {
      set({ error: formatError(error) })
      throw error
    }
  },
  applyEpisodeUpdate: (id, data) => {
    set((state) => ({
      episodes: state.episodes.map((e) =>
        e.id === id ? { ...e, ...data } : e
      ),
    }))
  },
}))
