import { render } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import AudioPlayer from '../AudioPlayer'

describe('AudioPlayer', () => {
  it('renders audio element with src', () => {
    const { container } = render(<AudioPlayer src="/outputs/test.mp3" />)
    const audio = container.querySelector('audio')
    expect(audio).toHaveAttribute('src', '/outputs/test.mp3')
  })
})
