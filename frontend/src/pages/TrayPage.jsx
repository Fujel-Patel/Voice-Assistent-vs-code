import { useState } from 'react'
import TrayMenu from '../components/TrayMenu'

/**
 * TrayPage.jsx — System tray window page (route: /tray)
 *
 * This page is rendered in a separate Electron BrowserWindow
 * that opens when the user clicks the system tray icon.
 * It shows the compact tray menu with quick actions.
 *
 * In dev mode, it renders centered on screen for testing.
 */

export default function TrayPage() {
  const [isListening, setIsListening] = useState(true)
  const [isMuted, setIsMuted] = useState(false)

  return (
    <div className="w-screen h-screen flex items-end justify-end p-4 bg-transparent">
      <TrayMenu
        isOpen
        isListening={isListening}
        isMuted={isMuted}
        onToggleListening={() => setIsListening((l) => !l)}
        onToggleMute={() => setIsMuted((m) => !m)}
        onShowWindow={() => {
          // In Electron: ipcRenderer.send('show-main-window')
          // Show main window – Electron IPC placeholder
        }}
        onOpenActivityLog={() => {
          // Open activity log – Electron IPC placeholder
        }}
        onOpenSettings={() => {
          // In Electron: ipcRenderer.send('navigate', '/settings')
          // Open settings – Electron IPC placeholder
        }}
        onQuit={() => {
          // In Electron: ipcRenderer.send('quit-app')
          // Quit Jarvis – Electron IPC placeholder
        }}
      />
    </div>
  )
}
