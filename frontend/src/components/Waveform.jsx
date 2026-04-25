import { useMemo } from 'react'

export default function Waveform({ audioLevel = 0, isActive = false }) {
  const bars = useMemo(() => new Array(28).fill(0).map((_, index) => index), [])

  return (
    <div className={`waveform ${isActive ? 'active' : ''}`}>
      {bars.map((index) => {
        const variance = 0.35 + Math.sin(index * 0.8) * 0.15
        const randomNoise = ((index * 123.45) % 1) // Simple deterministic noise
        const height = isActive ? 16 + (audioLevel * 48 + randomNoise * 22) * variance : 8 + (index % 3) * 4
        return (
          <span
            key={index}
            className='wave-bar'
            style={{
              height: `${Math.max(6, Math.min(72, height))}px`,
              animationDelay: `${index * 20}ms`,
            }}
          />
        )
      })}
    </div>
  )
}
