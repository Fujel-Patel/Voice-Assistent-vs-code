import React, { useEffect, useRef } from 'react'

export function AudioBarsWaveform({ visible, levels = [], color = '#00d4ff' }) {
  const canvasRef = useRef(null)
  const phaseRef = useRef(0)

  useEffect(() => {
    if (!visible) {
      return undefined
    }

    const canvas = canvasRef.current
    if (!canvas) {
      return undefined
    }

    const context = canvas.getContext('2d')
    if (!context) {
      return undefined
    }

    let raf = 0

    const draw = () => {
      const rect = canvas.getBoundingClientRect()
      const width = Math.max(1, Math.floor(rect.width))
      const height = Math.max(1, Math.floor(rect.height))
      const dpr = window.devicePixelRatio || 1

      if (canvas.width !== Math.floor(width * dpr) || canvas.height !== Math.floor(height * dpr)) {
        canvas.width = Math.floor(width * dpr)
        canvas.height = Math.floor(height * dpr)
      }

      context.setTransform(dpr, 0, 0, dpr, 0, 0)
      context.clearRect(0, 0, width, height)

      const barWidth = 3
      const gap = 4
      const barCount = Math.max(8, Math.floor((width + gap) / (barWidth + gap)))
      const mid = height / 2

      const sourceLevels = Array.isArray(levels) && levels.length ? levels : null
      phaseRef.current += 0.17

      for (let i = 0; i < barCount; i += 1) {
        const base = sourceLevels
          ? Number(sourceLevels[i % sourceLevels.length] || 0)
          : (Math.sin(phaseRef.current + i * 0.38) + 1) / 2

        const normalized = Math.max(0, Math.min(1, base))
        const barHeight = Math.max(4, normalized * 48)
        const x = i * (barWidth + gap)
        const y = mid - barHeight / 2

        context.fillStyle = color
        context.globalAlpha = 0.18 + normalized * 0.82
        context.beginPath()
        context.roundRect(x, y, barWidth, barHeight, 2)
        context.fill()
      }

      context.globalAlpha = 1
      raf = requestAnimationFrame(draw)
    }

    raf = requestAnimationFrame(draw)
    return () => cancelAnimationFrame(raf)
  }, [color, levels, visible])

  if (!visible) {
    return null
  }

  return <canvas className='voice-wave-canvas' ref={canvasRef} height={56} />
}

export default AudioBarsWaveform
