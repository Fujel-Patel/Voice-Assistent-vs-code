export default function SettingsToggle({ label, description, value, onChange, disabled = false }) {
  return (
    <label className='settings-control-row'>
      <div className='settings-control-copy'>
        <span>{label}</span>
        {description ? <small>{description}</small> : null}
      </div>
      <button
        type='button'
        role='switch'
        aria-checked={value}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange?.(!value)}
        className={`settings-toggle ${value ? 'on' : ''}`}
      >
        <span className='settings-toggle-thumb' />
      </button>
    </label>
  )
}
