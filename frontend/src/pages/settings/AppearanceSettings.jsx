import SettingsSection from '../../components/settings/SettingsSection'
import SettingsDropdown from '../../components/settings/SettingsDropdown'
import SettingsSlider from '../../components/settings/SettingsSlider'
import SettingsToggle from '../../components/settings/SettingsToggle'
import SettingsInput from '../../components/settings/SettingsInput'

export default function AppearanceSettings({ settings, onUpdate }) {
  return (
    <SettingsSection title='Appearance' description='Customize theme, visuals, and readability.'>
      <SettingsDropdown
        label='Theme'
        options={[
          { value: 'dark-sci-fi', label: 'Dark Sci-Fi' },
          { value: 'dark-minimal', label: 'Dark Minimal' },
          { value: 'cyberpunk', label: 'Cyberpunk' },
        ]}
        value={settings['ui.theme']}
        onChange={(value) => onUpdate('ui.theme', value)}
      />

      <SettingsDropdown
        label='Accent Color'
        options={[
          { value: 'cyan', label: 'Cyan' },
          { value: 'green', label: 'Green' },
          { value: 'amber', label: 'Amber' },
          { value: 'purple', label: 'Purple' },
          { value: 'custom', label: 'Custom' },
        ]}
        value={settings['ui.accent']}
        onChange={(value) => onUpdate('ui.accent', value)}
      />

      {settings['ui.accent'] === 'custom' ? (
        <SettingsInput
          label='Custom Accent HEX'
          value={settings['ui.accent_custom'] || '#00f5d4'}
          onChange={(value) => onUpdate('ui.accent_custom', value)}
        />
      ) : null}

      <SettingsDropdown
        label='HUD Animation Style'
        options={[
          { value: 'arc-reactor', label: 'Arc Reactor' },
          { value: 'pulse-ring', label: 'Pulse Ring' },
          { value: 'particle-field', label: 'Particle Field' },
          { value: 'minimal-dot', label: 'Minimal Dot' },
        ]}
        value={settings['ui.hud_style']}
        onChange={(value) => onUpdate('ui.hud_style', value)}
      />

      <SettingsSlider
        label='Animation Speed'
        min={0.5}
        max={2}
        step={0.1}
        value={settings['ui.animation_speed']}
        onChange={(value) => onUpdate('ui.animation_speed', value)}
        formatter={(value) => `${value.toFixed(1)}x`}
      />

      <SettingsToggle
        label='Reduced Animations'
        value={settings['ui.reduced_animations']}
        onChange={(value) => onUpdate('ui.reduced_animations', value)}
      />

      <SettingsSlider
        label='Window Opacity'
        min={50}
        max={100}
        step={1}
        value={settings['window.opacity']}
        onChange={(value) => onUpdate('window.opacity', value)}
        formatter={(value) => `${value}%`}
      />

      <SettingsDropdown
        label='Font Size'
        options={[
          { value: 'small', label: 'Small' },
          { value: 'normal', label: 'Normal' },
          { value: 'large', label: 'Large' },
        ]}
        value={settings['window.font_size']}
        onChange={(value) => onUpdate('window.font_size', value)}
      />
    </SettingsSection>
  )
}
