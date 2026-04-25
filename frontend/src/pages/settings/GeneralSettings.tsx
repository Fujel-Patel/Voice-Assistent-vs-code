import SettingsSection from '../../components/settings/SettingsSection'
import SettingsDropdown from '../../components/settings/SettingsDropdown'
import SettingsSlider from '../../components/settings/SettingsSlider'
import SettingsToggle from '../../components/settings/SettingsToggle'
import SettingsInput from '../../components/settings/SettingsInput'

const languages = [
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'Hindi' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'ja', label: 'Japanese' },
]

export default function GeneralSettings({ settings, onUpdate, onAutolaunchToggle }) {
  return (
    <>
      <SettingsSection title='General Controls' description='Core behavior and launch options.'>
        <SettingsDropdown
          label='Language'
          options={languages}
          value={settings['stt.language']}
          onChange={(value) => onUpdate('stt.language', value)}
        />

        <SettingsSlider
          label='Wake Word Sensitivity'
          min={0.3}
          max={0.7}
          step={0.1}
          value={settings['wake_word.sensitivity']}
          onChange={(value) => onUpdate('wake_word.sensitivity', value)}
          formatter={(value) => value.toFixed(1)}
        />

        <SettingsToggle
          label='Start With OS'
          description='Automatically launch Jarvis after login.'
          value={settings['window.start_with_os']}
          onChange={(value) => {
            onUpdate('window.start_with_os', value)
            onAutolaunchToggle?.(value)
          }}
        />

        <SettingsToggle
          label='Always On Top'
          value={settings['window.always_on_top']}
          onChange={(value) => onUpdate('window.always_on_top', value)}
        />

        <SettingsInput
          label='Hotkey Activation'
          value={settings['window.hotkey']}
          onChange={(value) => onUpdate('window.hotkey', value)}
          placeholder='Ctrl+Space'
        />

        <SettingsToggle
          label='Start Minimized'
          description='Hide in tray at startup.'
          value={settings['window.start_minimized']}
          onChange={(value) => onUpdate('window.start_minimized', value)}
        />
      </SettingsSection>
    </>
  )
}