/**
 * Frontend State Store — Settings
 * ==================================
 * Manages user settings state (synced with backend config).
 * Settings are persisted via the backend's config/user_config.yaml.
 *
 * Sends settings_update IPC messages to the backend when changed.
 */

import { createContext, useContext, useReducer } from 'react'

// ── Initial state (mirrors backend config/default.yaml) ──

const initialSettings = {
  // AI / Brain
  claudeModel: 'claude-sonnet-4-5',
  maxTokens: 1024,
  temperature: 0.7,

  // Voice
  whisperModel: 'small',
  wakeWord: 'jarvis',
  wakeWordSensitivity: 0.6,
  hotkeyEnabled: true,
  hotkey: 'ctrl+space',

  // TTS
  ttsProvider: 'elevenlabs',
  ttsVoiceId: '21m00Tcm4TlvDq8ikWAM',
  ttsStreaming: true,
  ttsVolume: 0.9,

  // Web Search
  webSearchProvider: 'brave',
  webSearchResults: 5,

  // Privacy / Security
  voiceAuthEnabled: false,
  longTermMemoryEnabled: true,

  // UI
  theme: 'dark',
  alwaysOnTop: false,
  showDebugConsole: false,
}

// ── Actions ────────────────────────────────────────────

// eslint-disable-next-line react-refresh/only-export-components
export const SettingsActions = {
  UPDATE_SETTING: 'UPDATE_SETTING',
  BULK_UPDATE:    'BULK_UPDATE',
  RESET:          'RESET',
}

function settingsReducer(state, action) {
  switch (action.type) {
    case SettingsActions.UPDATE_SETTING:
      return { ...state, [action.key]: action.value }
    case SettingsActions.BULK_UPDATE:
      return { ...state, ...action.payload }
    case SettingsActions.RESET:
      return { ...initialSettings }
    default:
      return state
  }
}

// ── Context ────────────────────────────────────────────

const SettingsContext = createContext(null)
const SettingsDispatchContext = createContext(null)

export function SettingsProvider({ children }) {
  const [state, dispatch] = useReducer(settingsReducer, initialSettings)
  return (
    <SettingsContext.Provider value={state}>
      <SettingsDispatchContext.Provider value={dispatch}>
        {children}
      </SettingsDispatchContext.Provider>
    </SettingsContext.Provider>
  )
}

// ── Hooks ──────────────────────────────────────────────

// eslint-disable-next-line react-refresh/only-export-components
export function useSettings() {
  const ctx = useContext(SettingsContext)
  if (!ctx) throw new Error('useSettings must be inside SettingsProvider')
  return ctx
}

// eslint-disable-next-line react-refresh/only-export-components
export function useSettingsDispatch() {
  const ctx = useContext(SettingsDispatchContext)
  if (!ctx) throw new Error('useSettingsDispatch must be inside SettingsProvider')
  return ctx
}

/**
 * Convenience hook: returns [settingValue, setter]
 * Similar to useState but backed by the settings store.
 *
 * Usage:
 *   const [volume, setVolume] = useSetting('ttsVolume')
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useSetting(key) {
  const settings = useSettings()
  const dispatch = useSettingsDispatch()
  return [
    settings[key],
    (value) => dispatch({ type: SettingsActions.UPDATE_SETTING, key, value }),
  ]
}
