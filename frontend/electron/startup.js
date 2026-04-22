import { spawn } from 'child_process'
import { dialog } from 'electron'
import net from 'net'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

export class StartupManager {
  constructor({ logger = console, wsPort = 8765, maxRestarts = 3 } = {}) {
    this.logger = logger
    this.wsPort = wsPort
    this.maxRestarts = maxRestarts
    this.backendProcess = null
    this.restartCount = 0
    this.shuttingDown = false
  }

  backendCommand() {
    const root = path.resolve(__dirname, '..', '..')
    const backendDir = path.join(root, 'backend')
    const python = path.join(backendDir, '.venv', 'bin', 'python')
    const args = ['main.py']
    return { python, args, cwd: backendDir }
  }

  async startup({ createMainWindow, setupTray, registerShortcuts, startMinimized = false }) {
    const running = await this.checkBackendRunning()
    if (!running) {
      await this.startBackend()
    }

    await this.waitForWebSocket(30000)

    const win = createMainWindow()
    setupTray()
    registerShortcuts()

    if (startMinimized) {
      win.hide()
    } else {
      win.show()
    }

    return win
  }

  async checkBackendRunning() {
    return new Promise((resolve) => {
      const sock = net.createConnection({ host: '127.0.0.1', port: this.wsPort })
      sock.on('connect', () => {
        sock.destroy()
        resolve(true)
      })
      sock.on('error', () => resolve(false))
    })
  }

  async startBackend() {
    const { python, args, cwd } = this.backendCommand()
    this.logger.info(`[startup] launching backend: ${python} ${args.join(' ')}`)

    this.backendProcess = spawn(python, args, {
      cwd,
      stdio: ['ignore', 'pipe', 'pipe'],
    })

    this.backendProcess.stdout.on('data', (buf) => {
      this.logger.info(`[backend] ${buf.toString().trim()}`)
    })
    this.backendProcess.stderr.on('data', (buf) => {
      this.logger.error(`[backend] ${buf.toString().trim()}`)
    })

    this.backendProcess.on('exit', async (code) => {
      if (this.shuttingDown) return
      if ((code || 0) === 0) return

      this.restartCount += 1
      if (this.restartCount > this.maxRestarts) {
        dialog.showErrorBox(
          'Jarvis Backend Crashed',
          'Backend failed repeatedly. Please check backend logs and restart Jarvis.',
        )
        return
      }

      this.logger.warn(`[startup] backend crashed code=${code}, restarting ${this.restartCount}/${this.maxRestarts}`)
      await this.startBackend()
    })
  }

  async waitForWebSocket(timeoutMs = 30000) {
    const start = Date.now()
    while (Date.now() - start < timeoutMs) {
      if (await this.checkBackendRunning()) {
        return true
      }
      await new Promise((resolve) => setTimeout(resolve, 500))
    }

    throw new Error('WebSocket backend did not become ready in time')
  }

  async restartBackend() {
    await this.stopBackend({ markShuttingDown: false })
    this.restartCount = 0
    await this.startBackend()
    await this.waitForWebSocket(30000)
  }

  async stopBackend({ markShuttingDown = true } = {}) {
    if (!this.backendProcess || this.backendProcess.killed) return

    this.shuttingDown = markShuttingDown
    this.backendProcess.kill('SIGTERM')
    await new Promise((resolve) => setTimeout(resolve, 1000))
    if (!this.backendProcess.killed) {
      this.backendProcess.kill('SIGKILL')
    }
    this.backendProcess = null
    if (!markShuttingDown) {
      this.shuttingDown = false
    }
  }
}
