import { createRequire } from 'module'

const require = createRequire(import.meta.url)

let AutoLaunch = null
try {
  AutoLaunch = require('auto-launch')
} catch {
  AutoLaunch = null
}

const launcher = AutoLaunch
  ? new AutoLaunch({
      name: 'Jarvis Voice Assistant',
      path: process.execPath,
      isHidden: true,
    })
  : null

export async function enable() {
  if (!launcher) return false
  const enabled = await launcher.isEnabled()
  if (!enabled) {
    await launcher.enable()
  }
  return true
}

export async function disable() {
  if (!launcher) return false
  const enabled = await launcher.isEnabled()
  if (enabled) {
    await launcher.disable()
  }
  return true
}

export async function isEnabled() {
  if (!launcher) return false
  return launcher.isEnabled()
}
