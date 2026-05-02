import { useEffect, useRef } from 'react'

const COLORS = {
  idle: '#4cc9f0',
  listening: '#00f5d4',
  thinking: '#ffb703',
  speaking: '#52b788',
}

export default function ArcReactor({ state = 'idle', audioLevel = 0 }) {
  const canvasRef = useRef(null)
  const frameRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    let angle = 0

    const resize = () => {
      const rect = canvas.getBoundingClientRect()
      canvas.width = rect.width * window.devicePixelRatio
      canvas.height = rect.height * window.devicePixelRatio
      ctx.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0)
    }

    const draw = () => {
      const w = canvas.clientWidth
      const h = canvas.clientHeight
      const cx = w / 2
      const cy = h / 2
      const base = Math.min(w, h) * 0.28
      const pulse = 1 + Math.sin(angle * 2.2) * 0.03 + audioLevel * 0.16
      const color = COLORS[state] || COLORS.idle

      ctx.clearRect(0, 0, w, h)

      ctx.save()
      ctx.translate(cx, cy)

      for (let i = 0; i < 3; i += 1) {
        const radius = base + i * 14
        ctx.beginPath()
        ctx.strokeStyle = color
        ctx.globalAlpha = 0.2 + i * 0.1
        ctx.lineWidth = 2
        ctx.arc(0, 0, radius * pulse, angle + i, angle + i + Math.PI * 1.4)
        ctx.stroke()
      }

      ctx.rotate(-angle * 0.7)
      ctx.beginPath()
      ctx.strokeStyle = color
      ctx.globalAlpha = 0.55
      ctx.lineWidth = 4
      ctx.arc(0, 0, base * 0.7, 0, Math.PI * 2)
      ctx.stroke()

      const grd = ctx.createRadialGradient(0, 0, 8, 0, 0, base * 0.7)
      grd.addColorStop(0, `${color}dd`)
      grd.addColorStop(1, `${color}08`)
      ctx.fillStyle = grd
      ctx.beginPath()
      ctx.arc(0, 0, base * 0.7, 0, Math.PI * 2)
      ctx.fill()

      ctx.restore()

      angle += state === 'thinking' ? 0.04 : 0.02
      frameRef.current = requestAnimationFrame(draw)
    }

    resize()
    window.addEventListener('resize', resize)
    frameRef.current = requestAnimationFrame(draw)

  return () => {
    window.removeEventListener('resize', resize)
    if (frameRef.current) {
      cancelAnimationFrame(frameRef.current)
      frameRef.current = null
    }
  }
  }, [state, audioLevel])

  return <canvas ref={canvasRef} className='arc-reactor-canvas' />
}
