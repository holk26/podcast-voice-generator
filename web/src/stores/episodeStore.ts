import { create } from 'zustand'
import { Episode, CreateEpisodeRequest } from '../types'
import { api } from '../api/client'
import { formatError } from '../utils/error'

interface EpisodeState {
  episodes: Episode[]
  loading: boolean
  error: string | null
  fetchEpisodes: () => Promise<void>
  createEpisode: (data: CreateEpisodeRequest) => Promise<Episode>
  deleteEpisode: (id: number) => Promise<void>
  applyEpisodeUpdate: (id: number, data: Partial<Episode>) => void
}

export const useEpisodeStore = create<EpisodeState>((set) => ({
  episodes: [],
  loading: false,
  error: null,
  fetchEpisodes: async () => {
    set({ loading: true, error: null })
    try {
      const episodes = await api.getEpisodes()
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
  applyEpisodeUpdate: (id, data) => {
    set((state) => ({
      episodes: state.episodes.map((e) =>
        e.id === id ? { ...e, ...data } : e
      ),
    }))
  },
}))
