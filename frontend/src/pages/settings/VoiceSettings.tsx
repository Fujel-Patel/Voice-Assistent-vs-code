import { useMemo, useState } from 'react'
import SettingsSection from '../../components/settings/SettingsSection'
import SettingsDropdown from '../../components/settings/SettingsDropdown'
import SettingsSlider from '../../components/settings/SettingsSlider'
import SettingsToggle from '../../components/settings/SettingsToggle'
import SettingsInput from '../../components/settings/SettingsInput'
import { UserPlus } from 'lucide-react'

export default function VoiceSettings({ settings, onUpdate, onOpenEnrollment, onVerifyPin }) {
  const [pin, setPin] = useState('')
  const [pinStatus, setPinStatus] = useState('')

  const micOptions = useMemo(
    () => [
      { value: 'default', label: 'Default Microphone' },
      { value: 'communications', label: 'Communication Device' },
    ],
    [],
  )

  const speakerOptions = useMemo(
    () => [
      { value: 'default', label: 'Default Output' },
      { value: 'communications', label: 'Communication Output' },
    ],
    [],
  )

  return (
    <>
      <SettingsSection title='Voice & Audio' description='Input, output, and speech synthesis configuration.'>
        <SettingsDropdown
          label='Microphone Input'
          options={micOptions}
          value={settings['audio.microphone_device']}
          onChange={(value) => onUpdate('audio.microphone_device', value)}
        />

        <SettingsDropdown
          label='Speaker Output'
          options={speakerOptions}
          value={settings['audio.speaker_device']}
          onChange={(value) => onUpdate('audio.speaker_device', value)}
        />

        <SettingsDropdown
          label='Voice Model'
          options={[
            { value: 'jarvis_classic', label: 'Jarvis Classic' },
            { value: 'jarvis_warm', label: 'Jarvis Warm' },
            { value: 'custom', label: 'Custom' },
          ]}
          value={settings['tts.voice_profile']}
          onChange={(value) => onUpdate('tts.voice_profile', value)}
        />

        <SettingsSlider
          label='Speaking Speed'
          min={0.5}
          max={2}
          step={0.1}
          value={settings['tts.speaking_rate']}
          onChange={(value) => onUpdate('tts.speaking_rate', value)}
          formatter={(value) => `${value.toFixed(1)}x`}
        />

        <SettingsSlider
          label='Speaking Volume'
          min={0}
          max={1}
          step={0.05}
          value={settings['tts.volume']}
          onChange={(value) => onUpdate('tts.volume', value)}
          formatter={(value) => `${Math.round(value * 100)}%`}
        />

        <SettingsDropdown
          label='TTS Engine'
          options={[
            { value: 'piper', label: 'Piper (Local, Fast)' },
            { value: 'kokoro', label: 'Kokoro (Local)' },
            { value: 'edge', label: 'Edge Neural (Cloud)' },
            { value: 'elevenlabs', label: 'ElevenLabs (Cloud)' },
            { value: 'local', label: 'System Local TTS' },
          ]}
          value={settings['tts.primary']}
          onChange={(value) => onUpdate('tts.primary', value)}
        />

        <SettingsDropdown
          label='STT Engine'
          options={[
            { value: 'moonshine', label: 'Moonshine Tiny (Local, Fast)' },
          ]}
          value={settings['stt.engine'] || 'moonshine'}
          onChange={(value) => onUpdate('stt.engine', value)}
        />

        <SettingsDropdown
          label='Moonshine Model'
          options={[
            { value: 'tiny', label: 'Tiny (Recommended)' },
          ]}
          value={settings['stt.model']}
          onChange={(value) => onUpdate('stt.model', value)}
        />

        <SettingsSlider
          label='Silence Detection Timeout'
          min={1}
          max={5}
          step={0.5}
          value={settings['audio.silence_stop_seconds']}
          onChange={(value) => onUpdate('audio.silence_stop_seconds', value)}
          formatter={(value) => `${value.toFixed(1)}s`}
        />
      </SettingsSection>

      <SettingsSection
        title='Voice Authentication (Experimental)'
        description='Convenience personalization only, not a security boundary.'
      >
        <SettingsToggle
          label='Enable Voice Authentication'
          description='Verify speaker before sensitive actions.'
          value={settings['auth.enabled']}
          onChange={(value) => onUpdate('auth.enabled', value)}
        />

        <SettingsDropdown
          label='Auth Mode'
          options={[
            { value: 'passive', label: 'Passive' },
            { value: 'challenge', label: 'Challenge' },
            { value: 'off', label: 'Off' },
          ]}
          value={settings['auth.mode']}
          onChange={(value) => onUpdate('auth.mode', value)}
        />

        <SettingsDropdown
          label='Verification Threshold'
          options={[
            { value: 'low', label: 'Low (Permissive)' },
            { value: 'medium', label: 'Medium (Recommended)' },
            { value: 'high', label: 'High (Strict)' },
          ]}
          value={settings['auth.threshold']}
          onChange={(value) => onUpdate('auth.threshold', value)}
        />

        <SettingsDropdown
          label='Liveness Challenge'
          options={[
            { value: 'always', label: 'Always' },
            { value: 'sensitive_only', label: 'Sensitive Operations Only' },
            { value: 'never', label: 'Never' },
          ]}
          value={settings['auth.liveness']}
          onChange={(value) => onUpdate('auth.liveness', value)}
        />

        <SettingsSlider
          label='Session Timeout'
          min={5}
          max={180}
          step={5}
          value={settings['auth.session_timeout_minutes']}
          onChange={(value) => onUpdate('auth.session_timeout_minutes', value)}
          formatter={(value) => `${value} min`}
        />

        <SettingsToggle
          label='Allow PIN Fallback'
          description='Allow manual verification after repeated voice failures.'
          value={settings['auth.pin_fallback']}
          onChange={(value) => onUpdate('auth.pin_fallback', value)}
        />

        {settings['auth.pin_fallback'] ? (
          <div className="flex flex-col gap-2">
            <SettingsInput
              label='Verify with PIN'
              type='password'
              value={pin}
              onChange={setPin}
              placeholder='Enter verification PIN'
              rightSlot={
                <button
                  type="button"
                  className="px-3 py-1.5 rounded-md text-xs font-medium bg-cyan-400/10 text-cyan-400 border border-cyan-400/20 hover:bg-cyan-400/20 transition-colors whitespace-nowrap"
                  onClick={async () => {
                    const result = await onVerifyPin?.(pin)
                    setPinStatus(result?.ok ? 'PIN verified' : 'Invalid PIN')
                    if (result?.ok) {
                      setPin('')
                    }
                  }}
                >
                  Verify PIN
                </button>
              }
            />
            {pinStatus ? <small className="text-xs text-muted-foreground">{pinStatus}</small> : null}
          </div>
        ) : null}

        <button
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium bg-violet-400/10 text-violet-400 border border-violet-400/20 hover:bg-violet-400/20 transition-all"
          onClick={onOpenEnrollment}
        >
          <UserPlus className="w-4 h-4" />
          Setup Voice Profile
        </button>
      </SettingsSection>
    </>
  )
}