import { create } from 'zustand'
import { Voice } from '../types'
import { api } from '../api/client'

interface VoiceState {
  voices: Voice[]
  loading: boolean
  error: string | null
  fetchVoices: () => Promise<void>
}

export const useVoiceStore = create<VoiceState>((set) => ({
  voices: [],
  loading: false,
  error: null,
  fetchVoices: async () => {
    set({ loading: true, error: null })
    try {
      const voices = await api.getVoices()
      set({ voices, loading: false })
    } catch (error) {
      set({ error: String(error), loading: false })
    }
  },
}))
