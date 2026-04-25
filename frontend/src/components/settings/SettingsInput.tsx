import { useMemo, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { cn } from '../../lib/utils'

export default function SettingsInput({
  label,
  type = 'text',
  value,
  onChange,
  validate,
  error,
  placeholder,
  rightSlot,
}) {
  const [visible, setVisible] = useState(false)
  const derivedError = useMemo(() => {
    if (error) return error
    if (!validate) return ''
    return validate(value) || ''
  }, [error, validate, value])

  const actualType = type === 'password' ? (visible ? 'text' : 'password') : type

  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-medium text-foreground">{label}</span>
      <div className={cn(
        "flex items-center rounded-lg bg-white/5 border transition-colors",
        derivedError ? "border-red-500/50" : "border-white/10 focus-within:border-cyan-400/30",
        "focus-within:ring-2 focus-within:ring-cyan-400/20"
      )}>
        <input
          type={actualType}
          value={value}
          placeholder={placeholder}
          aria-label={label}
          onChange={(event) => onChange?.(event.target.value)}
          className={cn(
            "flex-1 bg-transparent px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground/50",
            "focus:outline-none"
          )}
        />
        {type === 'password' ? (
          <button
            type="button"
            onClick={() => setVisible((v) => !v)}
            className="p-2 text-muted-foreground hover:text-foreground transition-colors"
          >
            {visible ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
          </button>
        ) : null}
        {rightSlot || null}
      </div>
      {derivedError ? (
        <small className="text-xs text-red-400">{derivedError}</small>
      ) : null}
    </label>
  )
}