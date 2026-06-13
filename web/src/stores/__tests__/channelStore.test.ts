import { describe, it, expect } from 'vitest'
import { useChannelStore } from '../channelStore'

describe('channelStore', () => {
  it('has empty channels by default', () => {
    const state = useChannelStore.getState()
    expect(state.channels).toEqual([])
    expect(state.loading).toBe(false)
  })
})
