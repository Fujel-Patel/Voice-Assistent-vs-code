import { useState } from 'react'
import SettingsSection from '../../components/settings/SettingsSection'
import SettingsDropdown from '../../components/settings/SettingsDropdown'
import SettingsSlider from '../../components/settings/SettingsSlider'
import SettingsToggle from '../../components/settings/SettingsToggle'
import SettingsInput from '../../components/settings/SettingsInput'

const PROVIDERS = [
  { value: 'claude', label: 'Anthropic Claude' },
  { value: 'gemini', label: 'Google Gemini' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'ollama', label: 'Ollama (Local)' },
  { value: 'groq', label: 'Groq' },
]

const MODEL_PRESETS = {
  claude: [
    { value: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
    { value: 'claude-opus-4-20250514', label: 'Claude Opus 4' },
  ],
  gemini: [
    { value: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
    { value: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash' },
  ],
  openrouter: [
    { value: 'openai/gpt-4o-mini', label: 'GPT-4o Mini' },
    { value: 'anthropic/claude-3.5-sonnet', label: 'Claude 3.5 Sonnet' },
    { value: 'google/gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
  ],
  ollama: [
    { value: 'llama3.2', label: 'Llama 3.2' },
    { value: 'qwen2.5', label: 'Qwen 2.5' },
    { value: 'mistral', label: 'Mistral' },
  ],
  groq: [
    { value: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B' },
    { value: 'mixtral-8x7b-32768', label: 'Mixtral 8x7B' },
  ],
}

function modelKeyForProvider(provider) {
  return `brain.models.${provider}`
}

export default function AISettings({ settings, onUpdate, onClearMemory, providerModels = {} }) {
  const [confirming, setConfirming] = useState(false)
  const provider = settings['brain.providers.default_provider'] || 'gemini'
  const modelKey = modelKeyForProvider(provider)
  const modelValue = settings[modelKey] || ''
  const discoveredModels = Array.isArray(providerModels[provider]) ? providerModels[provider] : []
  const baseOptions = discoveredModels.length ? discoveredModels : (MODEL_PRESETS[provider] || [])
  const modelOptions = [...baseOptions, { value: '__custom__', label: 'Custom Model ID' }]

  return (
    <>
      <SettingsSection title='AI & Brain' description='Model behavior, memory policy, and prompt controls.'>
        <SettingsDropdown
          label='Default Brain Provider'
          options={PROVIDERS}
          value={provider}
          onChange={(value) => onUpdate('brain.providers.default_provider', value)}
        />

        <SettingsDropdown
          label='Model Preset'
          options={modelOptions}
          value={baseOptions.some((item) => item.value === modelValue) ? modelValue : '__custom__'}
          onChange={(value) => {
            if (value === '__custom__') {
              return
            }
            onUpdate(modelKey, value)
          }}
        />

        <SettingsInput
          label='Model ID'
          value={modelValue}
          onChange={(value) => onUpdate(modelKey, value)}
          placeholder='Enter custom model ID'
        />

        <SettingsDropdown
          label='Response Length'
          options={[
            { value: 'brief', label: 'Brief' },
            { value: 'normal', label: 'Normal' },
            { value: 'detailed', label: 'Detailed' },
          ]}
          value={settings['response.length']}
          onChange={(value) => onUpdate('response.length', value)}
        />

        <SettingsDropdown
          label='Response Style'
          options={[
            { value: 'professional', label: 'Professional' },
            { value: 'casual', label: 'Casual' },
            { value: 'technical', label: 'Technical' },
            { value: 'custom', label: 'Custom' },
          ]}
          value={settings['response.style']}
          onChange={(value) => onUpdate('response.style', value)}
        />

        <SettingsSlider
          label='Conversation Memory Turns'
          min={10}
          max={50}
          step={10}
          value={settings['brain.short_term_turns']}
          onChange={(value) => onUpdate('brain.short_term_turns', value)}
          formatter={(value) => `${value} turns`}
        />

        <SettingsInput
          label='Custom System Prompt'
          value={settings['response.custom_prompt']}
          onChange={(value) => onUpdate('response.custom_prompt', value)}
          placeholder='Optional custom prompt'
        />

        <SettingsSlider
          label='Token Budget'
          min={2000}
          max={8000}
          step={250}
          value={settings['brain.token_budget']}
          onChange={(value) => onUpdate('brain.token_budget', value)}
          formatter={(value) => `${value} tokens`}
        />

        <SettingsToggle
          label='Streaming Responses'
          value={settings['brain.stream_chunks']}
          onChange={(value) => onUpdate('brain.stream_chunks', value)}
        />
      </SettingsSection>

      <SettingsSection title='Danger Zone' description='Conversation memory reset actions.' danger>
        {!confirming ? (
          <button className='settings-danger-btn' onClick={() => setConfirming(true)}>
            Clear Memory
          </button>
        ) : (
          <div className='settings-danger-confirm'>
            <p>This will clear conversation history.</p>
            <div>
              <button onClick={() => setConfirming(false)}>Cancel</button>
              <button
                onClick={() => {
                  onClearMemory?.('all')
                  setConfirming(false)
                }}
              >
                Clear Everything
              </button>
            </div>
          </div>
        )}
      </SettingsSection>
    </>
  )
}
