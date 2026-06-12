import { describe, it, expect } from 'vitest'
import { useVoiceStore } from '../voiceStore'

describe('voiceStore', () => {
  it('has empty voices by default', () => {
    const state = useVoiceStore.getState()
    expect(state.voices).toEqual([])
    expect(state.loading).toBe(false)
  })
})
