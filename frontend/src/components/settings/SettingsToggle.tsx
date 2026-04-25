import { motion } from 'framer-motion'
import { cn } from '../../lib/utils'

export default function SettingsToggle({ label, description, value, onChange, disabled = false }) {
  return (
    <label className="flex items-center justify-between gap-4 py-1">
      <div className="flex flex-col">
        <span className="text-sm font-medium text-foreground">{label}</span>
        {description ? (
          <span className="text-xs text-muted-foreground mt-0.5">{description}</span>
        ) : null}
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={value}
        aria-label={label}
        disabled={disabled}
        onClick={() => onChange?.(!value)}
        className={cn(
          "relative inline-flex h-6 w-11 items-center rounded-full transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:ring-offset-2 focus:ring-offset-background",
          value ? "bg-cyan-400" : "bg-white/10",
          disabled && "opacity-50 cursor-not-allowed"
        )}
      >
        <motion.span
          layout
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
          className={cn(
            "h-4 w-4 rounded-full bg-white shadow-lg",
            value ? "translate-x-6" : "translate-x-1"
          )}
        />
      </button>
    </label>
  )
}