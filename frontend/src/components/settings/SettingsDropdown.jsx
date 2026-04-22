export default function SettingsDropdown({ label, options, value, onChange }) {
  return (
    <label className='settings-control-column'>
      <span>{label}</span>
      <select
        value={value}
        aria-label={label}
        onChange={(event) => onChange?.(event.target.value)}
        className='settings-dropdown'
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  )
}
