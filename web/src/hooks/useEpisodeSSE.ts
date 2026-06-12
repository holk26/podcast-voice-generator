import { useEffect, useRef } from 'react'
import type { Episode } from '../types'

const TRACKED_STATUSES = new Set(['pending', 'running'])

export function useEpisodeSSE(
  episodes: Episode[],
  applyEpisodeUpdate: (id: number, data: Partial<Episode>) => void
) {
  const sourcesRef = useRef<Map<number, EventSource>>(new Map())
  const errorCountsRef = useRef<Map<number, number>>(new Map())
  const updateRef = useRef(applyEpisodeUpdate)
  updateRef.current = applyEpisodeUpdate

  useEffect(() => {
    const active = sourcesRef.current
    const errorCounts = errorCountsRef.current

    // Open connections for new pending/running episodes.
    episodes.forEach((episode) => {
      if (!TRACKED_STATUSES.has(episode.status)) return
      if (active.has(episode.id)) return

      errorCounts.delete(episode.id)
      const eventSource = new EventSource(`/api/episodes/${episode.id}/events`)
      active.set(episode.id, eventSource)

      eventSource.onopen = () => {
        errorCounts.delete(episode.id)
      }

      eventSource.onmessage = (event) => {
        errorCounts.delete(episode.id)
        try {
          const data = JSON.parse(event.data) as Partial<Episode>
          updateRef.current(episode.id, data)

          if (data.status === 'completed' || data.status === 'failed') {
            eventSource.close()
            active.delete(episode.id)
          }
        } catch {
          // Ignore malformed payloads.
        }
      }

      eventSource.onerror = () => {
        const count = (errorCounts.get(episode.id) || 0) + 1
        errorCounts.set(episode.id, count)
        console.error(`SSE error for episode ${episode.id} (attempt ${count})`)
        if (count > 5) {
          eventSource.close()
          active.delete(episode.id)
          errorCounts.delete(episode.id)
          updateRef.current(episode.id, {
            status: 'failed',
            error_message: 'Se perdió la conexión en tiempo real tras varios intentos.',
          })
        }
      }
    })

    // Close connections for episodes that are no longer pending/running.
    active.forEach((eventSource, id) => {
      const stillTracked = episodes.some(
        (e) => e.id === id && TRACKED_STATUSES.has(e.status)
      )
      if (!stillTracked) {
        eventSource.close()
        active.delete(id)
      }
    })
  }, [episodes])

  // Close all connections when the component unmounts.
  useEffect(() => {
    return () => {
      sourcesRef.current.forEach((eventSource) => eventSource.close())
      sourcesRef.current.clear()
    }
  }, [])
}
