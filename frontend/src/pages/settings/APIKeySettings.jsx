import { useMemo, useState } from 'react'
import SettingsSection from '../../components/settings/SettingsSection'
import SettingsDropdown from '../../components/settings/SettingsDropdown'
import SettingsInput from '../../components/settings/SettingsInput'

const rows = [
  {
    provider: 'anthropic',
    key: 'api.anthropic',
    label: 'Anthropic API Key',
    description: "Powers Jarvis's intelligence",
    link: 'https://console.anthropic.com',
  },
  {
    provider: 'gemini',
    key: 'api.gemini',
    label: 'Gemini API Key',
    description: "Powers Jarvis's Gemini provider",
    link: 'https://aistudio.google.com/app/apikey',
  },
  {
    provider: 'openrouter',
    key: 'api.openrouter',
    label: 'OpenRouter API Key',
    description: 'Powers multi-model routing via OpenRouter',
    link: 'https://openrouter.ai/keys',
  },
  {
    provider: 'groq',
    key: 'api.groq',
    label: 'Groq API Key',
    description: 'Powers Groq-hosted high-speed LLM models',
    link: 'https://console.groq.com/keys',
  },
  {
    provider: 'ollama',
    key: 'api.ollama',
    label: 'Ollama API Key',
    description: 'Optional for secured local Ollama gateways',
    link: 'https://ollama.com',
  },
  {
    provider: 'elevenlabs',
    key: 'api.elevenlabs',
    label: 'ElevenLabs API Key',
    description: "Powers Jarvis's voice",
    link: 'https://elevenlabs.io/app/settings/api-keys',
  },
]

const PROVIDER_MODEL_KEY = {
  anthropic: 'brain.models.claude',
  gemini: 'brain.models.gemini',
  groq: 'brain.models.groq',
  openrouter: 'brain.models.openrouter',
  ollama: 'brain.models.ollama',
}

export default function APIKeySettings({ settings, onUpdate, onValidate, onSaveAll, onModelsDiscovered }) {
  const [status, setStatus] = useState({})
  const [statusDetails, setStatusDetails] = useState({})
  const [providerModels, setProviderModels] = useState({})

  const pending = useMemo(() => Object.values(status).some((s) => s === 'pending'), [status])

  const verify = async (provider, keyValue) => {
    setStatus((prev) => ({ ...prev, [provider]: 'pending' }))
    const result = await onValidate?.(provider, keyValue)
    const valid = !!result?.valid
    setStatus((prev) => ({ ...prev, [provider]: valid ? 'valid' : 'invalid' }))
    setStatusDetails((prev) => ({
      ...prev,
      [provider]: result?.details || (valid ? 'Verified' : 'Validation failed'),
    }))

    const models = Array.isArray(result?.models) ? result.models : []
    if (!valid || !models.length) return

    setProviderModels((prev) => ({ ...prev, [provider]: models }))
    onModelsDiscovered?.(provider, models)
    const modelKey = PROVIDER_MODEL_KEY[provider]
    if (!modelKey) return

    const current = settings[modelKey] || ''
    const hasCurrent = models.some((model) => model.value === current)
    const chosen = hasCurrent ? current : models[0]?.value
    if (chosen && chosen !== current) {
      onUpdate(modelKey, chosen)
    }
  }

  return (
    <SettingsSection
      title='API Keys'
      description='Add only the keys you need. Keys stay local on your machine.'
    >
      <div className='settings-api-banner'>
        Verify each key before saving. Ollama verification checks local server reachability.
      </div>

      {rows.map((row) => (
        <div key={row.provider} className='settings-api-row'>
          <div>
            <h4>{row.label}</h4>
            <p>{row.description}</p>
            <a href={row.link} target='_blank' rel='noreferrer'>
              Get key
            </a>
          </div>

          <SettingsInput
            label={row.label}
            type='password'
            value={settings[row.key] || ''}
            onChange={(value) => onUpdate(row.key, value)}
            placeholder='Paste key here'
            rightSlot={
              <button
                type='button'
                className='settings-inline-btn'
                onClick={() => verify(row.provider, settings[row.key] || '')}
              >
                Verify
              </button>
            }
          />

          <div className={`settings-api-status ${status[row.provider] || 'idle'}`}>
            {status[row.provider] === 'valid' ? 'Verified' : null}
            {status[row.provider] === 'invalid' ? 'Invalid' : null}
            {status[row.provider] === 'pending' ? 'Checking...' : null}
            {(status[row.provider] === 'valid' || status[row.provider] === 'invalid') && statusDetails[row.provider]
              ? ` — ${statusDetails[row.provider]}`
              : null}
          </div>

          {providerModels[row.provider]?.length && PROVIDER_MODEL_KEY[row.provider] ? (
            <SettingsDropdown
              label={`${row.label} Model`}
              options={providerModels[row.provider]}
              value={settings[PROVIDER_MODEL_KEY[row.provider]] || providerModels[row.provider][0].value}
              onChange={(value) => onUpdate(PROVIDER_MODEL_KEY[row.provider], value)}
            />
          ) : null}
        </div>
      ))}

      <button className='settings-save-btn' disabled={pending} onClick={() => onSaveAll?.()}>
        Save All Keys
      </button>
    </SettingsSection>
  )
}
