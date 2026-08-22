import { create } from 'zustand'
import {
  Channel,
  ContentPlanEntry,
  CreateChannelRequest,
  CreatePlanEntryRequest,
  ActiveCrewJob,
  CrewJobEvent,
} from '../types'
import { api, sseUrl } from '../api/client'
import { formatError } from '../utils/error'

interface ChannelState {
  channels: Channel[]
  entries: Record<number, ContentPlanEntry[]>
  loading: boolean
  error: string | null
  activeJob: ActiveCrewJob | null
  targetMinutes: number
  setTargetMinutes: (minutes: number) => void
  fetchChannels: () => Promise<void>
  createChannel: (data: CreateChannelRequest) => Promise<Channel>
  updateChannel: (id: number, data: Partial<CreateChannelRequest>) => Promise<Channel>
  deleteChannel: (id: number) => Promise<void>
  publishChannel: (id: number) => Promise<void>
  unpublishChannel: (id: number) => Promise<void>
  fetchPlanEntries: (channelId: number) => Promise<void>
  generatePlan: (channelId: number, count?: number) => Promise<void>
  generateSeason: (channelId: number, weeks?: number) => Promise<void>
  _handleActionError: (error: unknown, channelId?: number) => Promise<void>
  createPlanEntry: (channelId: number, data: CreatePlanEntryRequest) => Promise<void>
  approveEntry: (entryId: number) => Promise<void>
  updateEntry: (entryId: number, data: CreatePlanEntryRequest) => Promise<void>
  rejectEntry: (entryId: number) => Promise<void>
  deleteEntry: (entryId: number) => Promise<void>
  clearJob: () => void
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

let jobSource: EventSource | null = null

function stopJobStream() {
  jobSource?.close()
  jobSource = null
}

export const useChannelStore = create<ChannelState>((set, get) => {
  /** Sigue un job CrewAI por SSE y vuelca sus eventos en activeJob. */
  function trackJob(jobId: string, kind: ActiveCrewJob['kind'], channelId?: number) {
    stopJobStream()
    set({
      activeJob: { id: jobId, kind, channelId, events: [], status: 'running' },
      loading: true,
      error: null,
    })

    const source = new EventSource(sseUrl(`/jobs/${jobId}/events`))
    jobSource = source

    source.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.step === '__status__') {
          stopJobStream()
          const ok = data.status === 'done'
          set((state) => ({
            activeJob: state.activeJob
              ? { ...state.activeJob, status: data.status, error: data.error ?? undefined }
              : null,
            loading: false,
            error: ok ? null : data.error || 'La generación falló',
          }))
          const cid = channelId ?? data.result?.channel_id
          if (ok && cid) get().fetchPlanEntries(cid)
          return
        }
        const jobEvent = data as CrewJobEvent
        set((state) =>
          state.activeJob
            ? { activeJob: { ...state.activeJob, events: [...state.activeJob.events, jobEvent] } }
            : {}
        )
      } catch {
        // Ignorar payloads mal formados
      }
    }

    source.onerror = () => {
      stopJobStream()
      set((state) => ({
        activeJob: state.activeJob
          ? { ...state.activeJob, status: 'error', error: 'Conexión perdida' }
          : null,
        loading: false,
        error: 'Se perdió la conexión en tiempo real.',
      }))
    }
  }

  return {
    channels: [],
    entries: {},
    loading: false,
    error: null,
    activeJob: null,
    targetMinutes: 10,

    setTargetMinutes: (minutes) => set({ targetMinutes: minutes }),

    clearJob: () => set({ activeJob: null }),

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

    updateChannel: async (id, data) => {
      set({ error: null })
      const channel = await api.updateChannel(id, data)
      set((state) => ({
        channels: state.channels.map((c) => (c.id === id ? channel : c)),
      }))
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

    publishChannel: async (id) => {
      set({ error: null })
      const channel = await api.publishChannel(id)
      set((state) => ({
        channels: state.channels.map((c) => (c.id === id ? channel : c)),
      }))
    },

    unpublishChannel: async (id) => {
      set({ error: null })
      const channel = await api.unpublishChannel(id)
      set((state) => ({
        channels: state.channels.map((c) => (c.id === id ? channel : c)),
      }))
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

    generatePlan: async (channelId, count = 5) => {
      set({ error: null })
      try {
        const { job_id } = await api.generatePlan(channelId, count)
        trackJob(job_id, 'plan', channelId)
      } catch (error) {
        await get()._handleActionError(error, channelId)
      }
    },

    generateSeason: async (channelId, weeks = 4) => {
      set({ error: null })
      try {
        const { job_id } = await api.generateSeason(channelId, weeks)
        trackJob(job_id, 'season', channelId)
      } catch (error) {
        await get()._handleActionError(error, channelId)
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
      set({ error: null })
      try {
        const { job_id } = await api.approvePlanEntry(entryId, get().targetMinutes)
        trackJob(job_id, 'script')
      } catch (error) {
        await get()._handleActionError(error)
      }
    },

    _handleActionError: async (error: unknown, channelId?: number) => {
      // 404 = canal/entrada borrados (estado obsoleto en la UI): refresca y avisa
      if (String(error).includes('404')) {
        await get().fetchChannels()
        if (channelId) await get().fetchPlanEntries(channelId)
        set({
          error: 'Ese canal o entrada ya no existe — lista actualizada.',
          loading: false,
        })
      } else {
        set({ error: formatError(error), loading: false })
      }
    },

    updateEntry: async (entryId, data) => {
      set({ error: null })
      const entry = await api.updatePlanEntry(entryId, data)
      set((state) => ({ entries: updateEntryInState(state.entries, entry) }))
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
  }
})
