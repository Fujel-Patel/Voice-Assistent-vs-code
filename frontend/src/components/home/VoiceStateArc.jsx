import React from 'react'

const STATE_META = {
  idle: { label: '', color: '#00d4ff' },
  listening: { label: '● LISTENING', color: '#00d4ff' },
  transcribing: { label: '◈ PROCESSING', color: '#a78bfa' },
  thinking: { label: '◈ THINKING', color: '#7c3aed' },
  speaking: { label: '◎ SPEAKING', color: '#34d399' },
  error: { label: '✕ ERROR', color: '#f87171' },
  wake_detected: { label: '● LISTENING', color: '#00d4ff' },
  verifying: { label: '◈ VERIFYING', color: '#a78bfa' },
}

export default function VoiceStateArc({ state = 'idle', audioLevel = 0 }) {
  const meta = STATE_META[state] || STATE_META.idle
  const speakingScale = state === 'speaking' ? 1 + Math.min(0.12, Math.max(0, audioLevel) * 0.12) : 1
  const listening = state === 'listening' || state === 'wake_detected'

  return (
    <div className={`voice-arc voice-arc-${state}`} style={{ '--arc-color': meta.color, '--arc-scale': speakingScale }}>
      <div className='voice-arc-core'>
        <span className='voice-arc-ring voice-arc-ring-primary' />
        <span className='voice-arc-ring voice-arc-ring-secondary' />
        <span className='voice-arc-ring voice-arc-ring-tertiary' />
        <span className='voice-arc-segment' />
        <span className='voice-arc-orb' />
        {listening ? (
          <>
            <span className='voice-arc-ripple voice-arc-ripple-a' />
            <span className='voice-arc-ripple voice-arc-ripple-b' />
          </>
        ) : null}
      </div>
      {meta.label ? <p className='voice-arc-label'>{meta.label}</p> : <p className='voice-arc-label voice-arc-label-hidden'>.</p>}
    </div>
  )
}
