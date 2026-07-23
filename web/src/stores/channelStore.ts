import { create } from 'zustand'
import {
  Channel,
  ContentPlanEntry,
  CreateChannelRequest,
  CreatePlanEntryRequest,
} from '../types'
import { api } from '../api/client'
import { formatError } from '../utils/error'

interface ChannelState {
  channels: Channel[]
  entries: Record<number, ContentPlanEntry[]>
  loading: boolean
  error: string | null
  fetchChannels: () => Promise<void>
  createChannel: (data: CreateChannelRequest) => Promise<Channel>
  deleteChannel: (id: number) => Promise<void>
  fetchPlanEntries: (channelId: number) => Promise<void>
  generatePlan: (channelId: number) => Promise<void>
  createPlanEntry: (channelId: number, data: CreatePlanEntryRequest) => Promise<void>
  approveEntry: (entryId: number) => Promise<void>
  rejectEntry: (entryId: number) => Promise<void>
  deleteEntry: (entryId: number) => Promise<void>
}

function updateEntryInState(
  entries: Record<number, ContentPlanEntry[]>,
  entry: ContentPlanEntry
): Record<number, ContentPlanEntry[]> {
  const channelEntries = entries[entry.channel_id] || []
  return {
    ...entries,
    [entry.channel_id]: channelEntries.map((e) => (e.id === entry.id ? entry : e)),
  }
}

export const useChannelStore = create<ChannelState>((set, get) => ({
  channels: [],
  entries: {},
  loading: false,
  error: null,

  fetchChannels: async () => {
    set({ loading: true, error: null })
    try {
      const channels = await api.getChannels()
      set({ channels, loading: false })
    } catch (error) {
      set({ error: formatError(error), loading: false })
    }
  },

  createChannel: async (data) => {
    set({ error: null })
    const channel = await api.createChannel(data)
    set((state) => ({ channels: [channel, ...state.channels] }))
    return channel
  },

  deleteChannel: async (id) => {
    set({ error: null })
    await api.deleteChannel(id)
    set((state) => {
      const { [id]: _, ...remaining } = state.entries
      return {
        channels: state.channels.filter((c) => c.id !== id),
        entries: remaining,
      }
    })
  },

  fetchPlanEntries: async (channelId) => {
    set({ loading: true, error: null })
    try {
      const entries = await api.getPlanEntries(channelId)
      set((state) => ({
        entries: { ...state.entries, [channelId]: entries },
        loading: false,
      }))
    } catch (error) {
      set({ error: formatError(error), loading: false })
    }
  },

  generatePlan: async (channelId) => {
    set({ loading: true, error: null })
    try {
      const entries = await api.generatePlan(channelId)
      set((state) => ({
        entries: { ...state.entries, [channelId]: entries },
        loading: false,
      }))
    } catch (error) {
      set({ error: formatError(error), loading: false })
    }
  },

  createPlanEntry: async (channelId, data) => {
    set({ error: null })
    const entry = await api.createPlanEntry(channelId, data)
    set((state) => ({
      entries: {
        ...state.entries,
        [channelId]: [entry, ...(state.entries[channelId] || [])],
      },
    }))
  },

  approveEntry: async (entryId) => {
    set({ loading: true, error: null })
    try {
      const entry = await api.approvePlanEntry(entryId)
      set((state) => ({ entries: updateEntryInState(state.entries, entry), loading: false }))
    } catch (error) {
      set({ error: formatError(error), loading: false })
    }
  },

  rejectEntry: async (entryId) => {
    set({ error: null })
    const entry = await api.rejectPlanEntry(entryId)
    set((state) => ({ entries: updateEntryInState(state.entries, entry) }))
  },

  deleteEntry: async (entryId) => {
    set({ error: null })
    const channelId = Object.keys(get().entries).find((key) =>
      get().entries[Number(key)].some((e) => e.id === entryId)
    )
    if (!channelId) return
    const cid = Number(channelId)
    await api.deletePlanEntry(entryId)
    set((state) => ({
      entries: {
        ...state.entries,
        [cid]: (state.entries[cid] || []).filter((e) => e.id !== entryId),
      },
    }))
  },
}))
