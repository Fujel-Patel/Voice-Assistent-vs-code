import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('jarvis', {
  window: {
    minimize: () => ipcRenderer.invoke('window:minimize'),
    hide: () => ipcRenderer.invoke('window:hide'),
    close: () => ipcRenderer.invoke('window:close'),
    toggleAlwaysOnTop: () => ipcRenderer.invoke('window:toggleAlwaysOnTop'),
    isAlwaysOnTop: () => ipcRenderer.invoke('window:isAlwaysOnTop'),
    isVisible: () => ipcRenderer.invoke('window:isVisible'),
  },
  backend: {
    getWsUrl: () => 'ws://localhost:8765/ws',
    restart: () => ipcRenderer.invoke('backend:restart'),
  },
  media: {
    requestMicrophoneAccess: () => ipcRenderer.invoke('media:requestMicrophoneAccess'),
  },
  autolaunch: {
    isEnabled: () => ipcRenderer.invoke('autolaunch:isEnabled'),
    toggle: (enabled) => ipcRenderer.invoke('autolaunch:toggle', enabled),
  },
  tray: {
    setState: (state) => ipcRenderer.send('tray:set-state', state),
    setLastResponse: (text) => ipcRenderer.send('tray:set-last-response', text),
    onListeningToggle: (callback) => {
      const handler = (_event, value) => callback(value)
      ipcRenderer.on('tray:listening-toggled', handler)
      return () => ipcRenderer.removeListener('tray:listening-toggled', handler)
    },
    onMuteToggle: (callback) => {
      const handler = (_event, value) => callback(value)
      ipcRenderer.on('tray:mute-toggled', handler)
      return () => ipcRenderer.removeListener('tray:mute-toggled', handler)
    },
  },
  onNavigate: (callback) => {
    const handler = (_event, route) => callback(route)
    ipcRenderer.on('navigate', handler)
    return () => ipcRenderer.removeListener('navigate', handler)
  },
})
