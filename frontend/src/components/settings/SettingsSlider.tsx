
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
  const percent = ((value - min) / (max - min)) * 100

  return (
    <label className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">{label}</span>
        {showValue ? (
          <strong className="text-sm font-mono text-cyan-400">{display}</strong>
        ) : null}
      </div>
      <div className="relative">
        <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-cyan-400 to-cyan-300 transition-all"
            style={{ width: `${percent}%` }}
          />
        </div>
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          aria-label={label}
          onChange={(event) => onChange?.(Number(event.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        />
      </div>
    </label>
  )
}