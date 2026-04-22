import { Menu, Tray, nativeImage } from 'electron'

function iconSvg(fill) {
  return `
<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
  <circle cx="16" cy="16" r="14" fill="${fill}" />
  <circle cx="16" cy="16" r="8" fill="#06121d" />
  <circle cx="16" cy="16" r="4" fill="${fill}" opacity="0.9" />
</svg>`.trim()
}

function iconForState(state = 'idle') {
  const colors = {
    idle: '#4b7b9f',
    listening: '#00f5d4',
    verifying: '#6dddff',
    thinking: '#ffb703',
    speaking: '#52b788',
    error: '#ef476f',
    disconnected: '#ef476f',
  }
  const svg = iconSvg(colors[state] || colors.idle)
  return nativeImage.createFromDataURL(`data:image/svg+xml;base64,${Buffer.from(svg).toString('base64')}`)
}

export function createTray(handlers) {
  const state = {
    voiceState: handlers.initialState || 'idle',
    listeningEnabled: true,
    isMuted: false,
    lastResponse: '',
  }

  const tray = new Tray(iconForState(state.voiceState))

  const buildMenu = () =>
    Menu.buildFromTemplate([
      { label: `JARVIS v1.0 (${state.voiceState})`, enabled: false },
      { type: 'separator' },
      {
        label: `Listening ${state.listeningEnabled ? 'ON' : 'OFF'}`,
        click: () => {
          state.listeningEnabled = !state.listeningEnabled
          handlers.onToggleListening?.(state.listeningEnabled)
          refresh()
        },
      },
      {
        label: `Mute ${state.isMuted ? 'ON' : 'OFF'}`,
        click: () => {
          state.isMuted = !state.isMuted
          handlers.onToggleMute?.(state.isMuted)
          refresh()
        },
      },
      { type: 'separator' },
      { label: 'Show Window (Ctrl+Shift+J)', click: handlers.onShowWindow },
      { label: 'Activity Log', click: handlers.onActivityLog },
      { label: 'Settings', click: handlers.onSettings },
      { label: 'Verify Identity', click: handlers.onVerifyIdentity },
      { type: 'separator' },
      { label: 'Restart Backend', click: handlers.onRestartBackend },
      { label: 'Copy Last Response', click: () => handlers.onCopyLastResponse?.(state.lastResponse) },
      { type: 'separator' },
      { label: 'Quit Jarvis', click: handlers.onQuit },
    ])

  const refresh = () => {
    tray.setImage(iconForState(state.voiceState))
    tray.setToolTip(`Jarvis: ${state.voiceState}${state.lastResponse ? `\n${state.lastResponse.slice(0, 80)}` : ''}`)
    tray.setContextMenu(buildMenu())
  }

  tray.on('click', handlers.onShowWindow)
  tray.on('double-click', () => {
    state.listeningEnabled = !state.listeningEnabled
    handlers.onToggleListening?.(state.listeningEnabled)
    refresh()
  })

  refresh()

  return {
    tray,
    updateState(nextState) {
      state.voiceState = nextState || 'idle'
      refresh()
    },
    updateLastResponse(text) {
      state.lastResponse = text || ''
      refresh()
    },
    setListening(enabled) {
      state.listeningEnabled = !!enabled
      refresh()
    },
    setMuted(muted) {
      state.isMuted = !!muted
      refresh()
    },
  }
}
