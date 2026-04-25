import { ExternalLink, RefreshCw, Github, FileText, Bug } from 'lucide-react'
import SettingsSection from '../../components/settings/SettingsSection'
import { cn } from '../../lib/utils'

export default function AboutSettings({ systemInfo, onCheckUpdates, onResetAll, usage }) {
  return (
    <>
      <SettingsSection title='About Jarvis' description='Version, runtime details, and resource usage.'>
        <div className="flex items-center gap-4 mb-4">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-400 to-violet-400 flex items-center justify-center">
            <div className="w-6 h-6 rounded-full bg-background/20" />
          </div>
          <div>
            <h4 className="text-lg font-semibold text-gradient">JARVIS Voice Assistant</h4>
            <p className="text-sm text-muted-foreground">Version 1.0.0</p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Electron', value: systemInfo?.electron || 'Unknown' },
            { label: 'Node.js', value: systemInfo?.node || 'Unknown' },
            { label: 'Python', value: systemInfo?.python || 'Unknown' },
            { label: 'OS', value: systemInfo?.platform || 'Unknown' },
            { label: 'Whisper', value: systemInfo?.whisper_model || 'small' },
            { label: 'TTS', value: systemInfo?.tts_engine || 'ElevenLabs' },
            { label: 'Claude Today', value: usage?.claude_today || '0 tokens' },
            { label: 'Cost Estimate', value: usage?.cost_today || '$0.00' },
          ].map(({ label, value }) => (
            <div key={label} className="flex flex-col gap-1 p-3 rounded-lg bg-white/5">
              <span className="text-xs text-muted-foreground">{label}</span>
              <strong className="text-sm font-mono text-foreground">{value}</strong>
            </div>
          ))}
        </div>

        <div className="flex flex-wrap gap-2">
          {[
            { href: 'https://github.com', label: 'GitHub', icon: Github },
            { href: 'https://docs.github.com', label: 'Documentation', icon: FileText },
            { href: 'https://github.com/issues', label: 'Report Bug', icon: Bug },
          ].map(({ href, label, icon: Icon }) => (
            <a
              key={label}
              href={href}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-3 py-2 rounded-lg text-xs font-medium bg-white/5 text-muted-foreground hover:text-foreground hover:bg-white/10 border border-white/10 transition-all"
            >
              <Icon className="w-3.5 h-3.5" />
              {label}
              <ExternalLink className="w-3 h-3 opacity-50" />
            </a>
          ))}
        </div>

        <div className="flex gap-2">
          <button
            className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium bg-white/5 text-foreground border border-white/10 hover:bg-white/10 transition-colors"
            onClick={onCheckUpdates}
          >
            <RefreshCw className="w-4 h-4" />
            Check for Updates
          </button>
          <button
            className={cn(
              "px-4 py-2.5 rounded-lg text-sm font-medium transition-all",
              "text-red-400 bg-red-500/10 border border-red-500/20 hover:bg-red-500/20"
            )}
            onClick={onResetAll}
          >
            Reset All Settings
          </button>
        </div>
      </SettingsSection>
    </>
  )
}