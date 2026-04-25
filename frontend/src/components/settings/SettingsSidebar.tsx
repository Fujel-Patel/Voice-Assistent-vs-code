import { Settings, Mic, KeyRound, Brain, Info, Palette } from 'lucide-react'

const NAV = [
  { id: 'general', icon: Settings, label: 'General' },
  { id: 'voice', icon: Mic, label: 'Voice & Audio' },
  { id: 'api', icon: KeyRound, label: 'API Keys' },
  { id: 'ai', icon: Brain, label: 'AI & Brain' },
  { id: 'appearance', icon: Palette, label: 'Appearance' },
  { id: 'about', icon: Info, label: 'About' },
]

export default function SettingsSidebar({ active, onChange }) {
  return (
    <aside className="flex flex-col gap-1 p-2 rounded-xl glass">
      {NAV.map((item) => {
        const Icon = item.icon
        const isActive = active === item.id
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onChange?.(item.id)}
            className={`
              flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200
              ${isActive
                ? 'bg-cyan-400/10 text-cyan-400 border border-cyan-400/20'
                : 'text-muted-foreground hover:text-foreground hover:bg-white/5'
              }
            `}
          >
            <Icon className="w-4 h-4" strokeWidth={isActive ? 2.5 : 2} />
            <span>{item.label}</span>
          </button>
        )
      })}
    </aside>
  )
}