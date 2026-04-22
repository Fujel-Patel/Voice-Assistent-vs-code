export default function SettingsSlider({
  label,
  min,
  max,
  step = 1,
  value,
  onChange,
  showValue = true,
  formatter,
}) {
  const display = formatter ? formatter(value) : value

  return (
    <label className='settings-control-column'>
      <div className='settings-control-head'>
        <span>{label}</span>
        {showValue ? <strong>{display}</strong> : null}
      </div>
      <input
        type='range'
        min={min}
        max={max}
        step={step}
        value={value}
        aria-label={label}
        onChange={(event) => onChange?.(Number(event.target.value))}
        className='settings-slider'
      />
    </label>
  )
}
