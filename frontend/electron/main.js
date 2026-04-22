import { app, BrowserWindow, clipboard, dialog, globalShortcut, ipcMain } from 'electron'
import path from 'path'
import { fileURLToPath } from 'url'

import * as autolaunch from './autolaunch.js'
import { StartupManager } from './startup.js'
import { createTray } from './tray.js'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const isDev = process.env.NODE_ENV !== 'production'
const devUrl = 'http://localhost:5173'

app.commandLine.appendSwitch('disable-background-timer-throttling')
app.commandLine.appendSwitch('disable-renderer-backgrounding')
app.commandLine.appendSwitch('disable-backgrounding-occluded-windows')

let mainWindow = null
let trayController = null
let isQuitting = false
let startupManager = new StartupManager({ logger: console })

function createMainWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 900,
    minHeight: 620,
    frame: false,
    transparent: true,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
      backgroundThrottling: false,
    },
  })

  const session = win.webContents.session
  session.setPermissionCheckHandler((_webContents, permission, requestingOrigin) => {
    if (permission === 'media' || permission === 'microphone') {
      return requestingOrigin.startsWith('http://localhost:5173') || requestingOrigin.startsWith('file://')
    }
    return true
  })

  session.setPermissionRequestHandler((_webContents, permission, callback, details) => {
    if (permission === 'media' || permission === 'microphone') {
      const origin = details?.requestingUrl || ''
      const trusted = origin.startsWith('http://localhost:5173') || origin.startsWith('file://')
      callback(trusted)
      return
    }
    callback(true)
  })

  if (isDev) {
    win.loadURL(devUrl)
  } else {
    win.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  win.on('close', (event) => {
    if (isQuitting) return
    event.preventDefault()
    win.hide()
  })

  return win
}

function showMainWindow() {
  if (!mainWindow) return
  if (mainWindow.isMinimized()) {
    mainWindow.restore()
  }
  mainWindow.show()
  mainWindow.focus()
}

function registerShortcuts() {
  globalShortcut.register('CommandOrControl+Shift+J', () => {
    if (!mainWindow) return
    if (mainWindow.isVisible()) mainWindow.hide()
    else showMainWindow()
  })

  globalShortcut.register('Escape', () => {
    if (mainWindow?.isVisible()) mainWindow.hide()
  })
}

function setupIpc() {
  ipcMain.handle('window:minimize', () => mainWindow?.minimize())
  ipcMain.handle('window:hide', () => mainWindow?.hide())
  ipcMain.handle('window:close', () => mainWindow?.hide())
  ipcMain.handle('window:toggleAlwaysOnTop', () => {
    if (!mainWindow) return false
    const next = !mainWindow.isAlwaysOnTop()
    mainWindow.setAlwaysOnTop(next)
    return next
  })
  ipcMain.handle('window:isAlwaysOnTop', () => mainWindow?.isAlwaysOnTop() ?? false)
  ipcMain.handle('window:isVisible', () => mainWindow?.isVisible() ?? false)

  ipcMain.handle('autolaunch:isEnabled', async () => autolaunch.isEnabled())
  ipcMain.handle('autolaunch:toggle', async (_event, enabled) => {
    if (enabled) await autolaunch.enable()
    else await autolaunch.disable()
    return autolaunch.isEnabled()
  })

  ipcMain.handle('backend:restart', async () => {
    await startupManager.restartBackend()
    return true
  })

  ipcMain.handle('media:requestMicrophoneAccess', async () => {
    if (!mainWindow) return false

    try {
      if (typeof mainWindow.webContents.session.setDisplayMediaRequestHandler === 'function') {
        // No-op check for media capability on this Electron build.
      }

      const granted = await mainWindow.webContents.executeJavaScript(
        `
          (async () => {
            try {
              const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
              stream.getTracks().forEach((t) => t.stop());
              return true;
            } catch {
              return false;
            }
          })();
        `,
        true,
      )
      return !!granted
    } catch {
      return false
    }
  })

  ipcMain.on('tray:set-state', (_event, state) => {
    trayController?.updateState(state)
  })
  ipcMain.on('tray:set-last-response', (_event, text) => {
    trayController?.updateLastResponse(text)
  })
}

function setupTray() {
  trayController = createTray({
    initialState: 'idle',
    onShowWindow: showMainWindow,
    onToggleListening: (enabled) => {
      mainWindow?.webContents.send('tray:listening-toggled', enabled)
      trayController?.setListening(enabled)
    },
    onToggleMute: (muted) => {
      mainWindow?.webContents.send('tray:mute-toggled', muted)
      trayController?.setMuted(muted)
    },
    onActivityLog: () => {
      showMainWindow()
      mainWindow?.webContents.send('navigate', '/')
    },
    onSettings: () => {
      showMainWindow()
      mainWindow?.webContents.send('navigate', '/settings')
    },
    onVerifyIdentity: () => {
      showMainWindow()
      mainWindow?.webContents.send('navigate', '/voice-enrollment')
    },
    onRestartBackend: async () => {
      try {
        await startupManager.restartBackend()
        dialog.showMessageBox({ message: 'Backend restarted successfully.', type: 'info' })
      } catch (err) {
        dialog.showErrorBox('Restart Failed', String(err))
      }
    },
    onCopyLastResponse: (text) => {
      clipboard.writeText(text || '')
    },
    onQuit: () => {
      isQuitting = true
      app.quit()
    },
  })
}

app.whenReady().then(async () => {
  try {
    await startupManager.startup({
      createMainWindow: () => {
        mainWindow = createMainWindow()
        return mainWindow
      },
      setupTray,
      registerShortcuts,
      startMinimized: process.env.JARVIS_START_MINIMIZED === '1',
    })
  } catch (error) {
    dialog.showErrorBox('Jarvis Startup Error', String(error))
    app.quit()
    return
  }

  setupIpc()
})

app.on('activate', () => {
  if (!mainWindow) {
    mainWindow = createMainWindow()
  }
  showMainWindow()
})

app.on('before-quit', async () => {
  isQuitting = true
  await startupManager.stopBackend()
})

app.on('will-quit', () => {
  globalShortcut.unregisterAll()
})
