import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { ArrowLeft, LayoutDashboard } from 'lucide-react'
import SettingsSidebar from '../components/settings/SettingsSidebar'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAppStore } from '../store/appStore'
import AISettings from './settings/AISettings'
import APIKeySettings from './settings/APIKeySettings'
import AboutSettings from './settings/AboutSettings'
import AppearanceSettings from './settings/AppearanceSettings'
import GeneralSettings from './settings/GeneralSettings'
import VoiceSettings from './settings/VoiceSettings'

export default function SettingsPage() {
  const navigate = useNavigate()
  const websocket = useWebSocket()

  const settings = useAppStore((state) => state.settings)
  const updateSettings = useAppStore((state) => state.updateSettings)
  const updateManySettings = useAppStore((state) => state.updateManySettings)
  const activeSettingsSection = useAppStore((state) => state.activeSettingsSection)
  const setActiveSettingsSection = useAppStore((state) => state.setActiveSettingsSection)
  const addToast = useAppStore((state) => state.addToast)

  const [systemInfo, setSystemInfo] = useState(null)
  const [providerModels, setProviderModels] = useState({})

  useEffect(() => {
    const unsubSettings = websocket.subscribe('settings_response', (payload) => {
      if (!payload?.ok) {
        addToast({ type: 'warning', title: 'Settings error', message: payload?.error || 'Unable to load settings' })
        return
      }
      updateManySettings(payload.settings || {})
      if (payload.system_info) setSystemInfo(payload.system_info)
    })

    const unsubUpdated = websocket.subscribe('settings_updated', (payload) => {
      if (!payload?.ok) {
        addToast({ type: 'warning', title: 'Settings update failed', message: payload?.error || 'Update failed' })
        return
      }

      updateManySettings(payload.settings || payload.updated || {})
      addToast({
        type: 'success',
        title: 'Saved',
        message: payload.restart_required ? 'Saved. Restart required for full effect.' : 'Setting saved successfully',
      })
    })

    const unsubSync = websocket.subscribe('settings_sync', (payload) => {
      if (payload?.ok) {
        updateManySettings(payload.settings || payload.updated || {})
      }
    })

    websocket.sendMessage({
      type: 'get_settings',
      payload: {},
    })

    return () => {
      unsubSettings?.()
      unsubUpdated?.()
      unsubSync?.()
    }
  }, [addToast, updateManySettings, websocket])

  const onUpdate = useCallback(
    (key, value) => {
      updateSettings(key, value)
      websocket.sendMessage({
        type: 'update_setting',
        payload: { key, value },
      })
    },
    [updateSettings, websocket],
  )

  const onValidateApiKey = useCallback(
    (provider, key) =>
      new Promise((resolve) => {
        const cleanup = websocket.subscribe('api_key_validation', (payload) => {
          if (payload?.provider !== provider) {
            return
          }
          cleanup?.()
          resolve(payload)
        })

        websocket.sendMessage({
          type: 'validate_api_key',
          payload: { provider, key },
        })
      }),
    [websocket],
  )

  const onSaveApiKeys = useCallback(() => {
    websocket.sendMessage({
      type: 'update_settings_bulk',
      payload: {
        settings: {
          'api.anthropic': settings['api.anthropic'] || '',
          'api.gemini': settings['api.gemini'] || '',
          'api.openrouter': settings['api.openrouter'] || '',
          'api.ollama': settings['api.ollama'] || '',
          'api.elevenlabs': settings['api.elevenlabs'] || '',
        },
      },
    })
  }, [settings, websocket])

  const onResetAll = useCallback(() => {
    websocket.sendMessage({ type: 'reset_settings', payload: {} })
  }, [websocket])

  const onAutolaunchToggle = useCallback((enabled) => {
    window.jarvis?.autolaunch?.toggle?.(enabled)
  }, [])

  const onVerifyPin = useCallback(
    (pin) =>
      new Promise((resolve) => {
        const cleanup = websocket.subscribe('pin_result', (payload) => {
          cleanup?.()
          if (payload?.ok) {
            addToast({ type: 'success', title: 'Verified', message: payload?.message || 'PIN accepted.' })
          } else {
            addToast({ type: 'warning', title: 'PIN rejected', message: payload?.message || 'Invalid PIN.' })
          }
          resolve(payload || { ok: false })
        })

        websocket.sendMessage({
          type: 'verify_pin',
          payload: { pin },
        })
      }),
    [addToast, websocket],
  )

  const sectionContent = useMemo(() => {
    if (activeSettingsSection === 'general') {
      return <GeneralSettings settings={settings} onUpdate={onUpdate} onAutolaunchToggle={onAutolaunchToggle} />
    }
    if (activeSettingsSection === 'voice') {
      return (
        <VoiceSettings
          settings={settings}
          onUpdate={onUpdate}
          onOpenEnrollment={() => navigate('/voice-enrollment')}
          onVerifyPin={onVerifyPin}
        />
      )
    }
    if (activeSettingsSection === 'ai') {
      return (
        <AISettings
          settings={settings}
          onUpdate={onUpdate}
          onClearMemory={() => {}}
          providerModels={providerModels}
        />
      )
    }
    if (activeSettingsSection === 'appearance') {
      return <AppearanceSettings settings={settings} onUpdate={onUpdate} />
    }
    if (activeSettingsSection === 'api') {
      return (
        <APIKeySettings
          settings={settings}
          onUpdate={onUpdate}
          onValidate={onValidateApiKey}
          onSaveAll={onSaveApiKeys}
          onModelsDiscovered={(provider, models) => {
            setProviderModels((prev) => ({
              ...prev,
              [provider]: Array.isArray(models) ? models : [],
            }))
          }}
        />
      )
    }
    return (
      <AboutSettings
        systemInfo={systemInfo}
        usage={null}
        onCheckUpdates={() => addToast({ type: 'info', title: 'No updates', message: 'You are on the latest version.' })}
        onResetAll={onResetAll}
      />
    )
  }, [
    activeSettingsSection,
    addToast,
    navigate,
    onAutolaunchToggle,
    onResetAll,
    onSaveApiKeys,
    onVerifyPin,
    onUpdate,
    onValidateApiKey,
    providerModels,
    settings,
    systemInfo,
  ])

  return (
    <div className="min-h-full p-6">
      <header className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">Jarvis Settings</h2>
          <p className="mt-1 text-muted-foreground">Tune behavior, voice, AI, and visual interface in real time.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            className="flex items-center justify-center gap-2 w-36 px-4 py-2.5 rounded-xl text-sm font-semibold bg-white/5 text-muted-foreground hover:text-foreground hover:bg-white/10 border border-white/10 transition-all shadow-sm"
            onClick={() => navigate('/')}
          >
            <ArrowLeft className="w-4 h-4" />
            HUD View
          </button>
          <button
            className="flex items-center justify-center gap-2 w-36 px-4 py-2.5 rounded-xl text-sm font-semibold bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20 transition-all shadow-sm"
            onClick={() => navigate('/dashboard')}
          >
            <LayoutDashboard className="w-4 h-4" />
            Dashboard
          </button>
        </div>
      </header>

      <div className="flex gap-6">
        <SettingsSidebar active={activeSettingsSection} onChange={setActiveSettingsSection} />
        <main className="flex-1 min-w-0">
          <AnimatePresence mode="wait">
            <motion.div
              key={activeSettingsSection}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              className="space-y-6"
            >
              {sectionContent}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  )
}