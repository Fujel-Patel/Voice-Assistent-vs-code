export const WS_STATES = {
  CONNECTING: 'connecting',
  CONNECTED: 'connected',
  DISCONNECTED: 'disconnected',
  RECONNECTING: 'reconnecting',
}

export const VOICE_STATES = ['idle', 'wake_detected', 'listening', 'transcribing', 'verifying', 'thinking', 'speaking']

export const STATE_VISUALS = {
  idle: {
    color: 'var(--accent-cyan-dim)',
    pulseSpeed: 'slow',
    ringSize: 'normal',
    glowIntensity: 0.3,
  },
  listening: {
    color: 'var(--accent-cyan)',
    pulseSpeed: 'fast',
    ringSize: 'expanded',
    glowIntensity: 0.7,
    showRipples: true,
  },
  thinking: {
    color: 'var(--accent-amber)',
    pulseSpeed: 'medium',
    ringSize: 'normal',
    rotationSpeed: 'fast',
    glowIntensity: 0.55,
    showParticles: true,
  },
  verifying: {
    color: 'var(--accent-cyan)',
    pulseSpeed: 'medium',
    ringSize: 'normal',
    glowIntensity: 0.8,
  },
  speaking: {
    color: 'var(--accent-green)',
    pulseSpeed: 'rhythmic',
    ringSize: 'normal',
    glowIntensity: 0.6,
    pulseWithAudio: true,
  },
}

export const BACKEND_WS_URL =
  typeof window !== 'undefined' && window.jarvis?.backend?.getWsUrl
    ? window.jarvis.backend.getWsUrl()
    : 'ws://localhost:8765/ws'

const resolveBackendHealthUrl = () => {
  try {
    const wsUrl = new URL(BACKEND_WS_URL)
    const protocol = wsUrl.protocol === 'wss:' ? 'https:' : 'http:'
    const port = wsUrl.port || (wsUrl.protocol === 'wss:' ? '443' : '80')
    return `${protocol}//${wsUrl.hostname}:${port}/health`
  } catch {
    return 'http://127.0.0.1:8765/health'
  }
}

export const BACKEND_HEALTH_URL = resolveBackendHealthUrl()

export const TOAST_TYPES = {
  info: 'info',
  success: 'success',
  warning: 'warning',
}
