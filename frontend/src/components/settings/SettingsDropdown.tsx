import { cn } from '../../lib/utils'
import { ChevronDown } from 'lucide-react'

export default function SettingsDropdown({ label, options, value, onChange }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm font-medium text-foreground">{label}</span>
      <div className="relative">
        <select
          value={value}
          aria-label={label}
          onChange={(event) => onChange?.(event.target.value)}
          className={cn(
            "w-full appearance-none rounded-lg px-3 py-2 pr-10 text-sm",
            "bg-white/5 border border-white/10",
            "text-foreground",
            "focus:outline-none focus:ring-2 focus:ring-cyan-400/50 focus:border-cyan-400/30",
            "hover:border-white/20 transition-colors"
          )}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
      </div>
    </label>
  )
}