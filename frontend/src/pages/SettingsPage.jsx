import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
    settings,
    systemInfo,
  ])

  return (
    <div className='settings-page'>
      <header className='settings-page-header'>
        <div>
          <h2>Jarvis Settings</h2>
          <p>Tune behavior, voice, AI, and visual interface in real time.</p>
        </div>
        <div className='settings-page-actions'>
          <button className='settings-return-btn' onClick={() => navigate('/')}>
            Return to HUD
          </button>
          <button className='settings-return-btn' onClick={() => navigate('/dashboard')}>
            Open Dashboard
          </button>
        </div>
      </header>

      <div className='settings-layout'>
        <SettingsSidebar active={activeSettingsSection} onChange={setActiveSettingsSection} />
        <main className='settings-content'>{sectionContent}</main>
      </div>
    </div>
  )
}
