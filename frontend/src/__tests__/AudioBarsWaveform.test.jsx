import React from 'react'
import { render } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AudioBarsWaveform } from '../components/home/AudioBarsWaveform'

describe('AudioBarsWaveform', () => {
  it('renders nothing when hidden', () => {
    const { container } = render(<AudioBarsWaveform visible={false} levels={[]} color='#00d4ff' />)
    expect(container.querySelector('canvas')).toBeNull()
  })

  it('renders canvas when visible', () => {
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
      setTransform: () => {},
      clearRect: () => {},
      beginPath: () => {},
      roundRect: () => {},
      fill: () => {},
      fillStyle: '',
      globalAlpha: 1,
    })
    const requestSpy = vi.spyOn(window, 'requestAnimationFrame').mockImplementation(() => 1)
    const cancelSpy = vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {})

    const { container, unmount } = render(<AudioBarsWaveform visible levels={[0.2, 0.4, 0.6]} color='#10b981' />)
    expect(container.querySelector('canvas')).toBeTruthy()

    unmount()
    vi.restoreAllMocks()
  })
})
