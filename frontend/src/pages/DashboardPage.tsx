import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Settings, Wifi, WifiOff, Mic, MicOff, Brain, MessageSquare, Clock } from 'lucide-react'
import { useAppStore } from '../store/appStore'
import { cn } from '../lib/utils'

function StatusBadge({ status, icon: Icon }) {
  const isConnected = status && status !== 'disconnected'
  return (
    <div className={cn(
      "flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono",
      isConnected ? "bg-green-400/10 text-green-400 border border-green-400/20" : "bg-red-400/10 text-red-400 border border-red-400/20"
    )}>
      <Icon className="w-3.5 h-3.5" />
      {String(status || 'disconnected').toUpperCase()}
    </div>
  )
}

function StatRow({ label, value, ok }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-white/5 last:border-0">
      <span className="text-sm text-muted-foreground">{label}</span>
      <strong className={cn(
        "text-sm font-mono",
        ok === true ? "text-green-400" : ok === false ? "text-red-400" : "text-foreground"
      )}>
        {value}
      </strong>
    </div>
  )
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const connectionState = useAppStore((state) => state.connectionState)
  const voiceState = useAppStore((state) => state.voiceState)
  const healthStatus = useAppStore((state) => state.healthStatus)
  const authStatus = useAppStore((state) => state.authStatus)
  const messages = useAppStore((state) => state.messages)
  const currentTranscription = useAppStore((state) => state.currentTranscription)
  const currentResponse = useAppStore((state) => state.currentResponse)

  const recentMessages = useMemo(() => messages.slice(-12).reverse(), [messages])

  return (
    <div className="min-h-full p-6 space-y-6">
      <header className="flex flex-col sm:flex-row sm:items-center justify-between mb-8 gap-6">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">System Dashboard</h2>
          <p className="mt-1 text-muted-foreground">Live overview of connection, voice pipeline, auth, and transcript streams.</p>
        </div>
        <div className="flex items-center gap-3">
          <button
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-white/5 text-muted-foreground hover:text-foreground hover:bg-white/10 border border-white/10 transition-all shadow-sm"
            onClick={() => navigate('/')}
          >
            <ArrowLeft className="w-4 h-4" />
            HUD View
          </button>
          <button
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20 transition-all shadow-sm"
            onClick={() => navigate('/settings')}
          >
            <Settings className="w-4 h-4" />
            Settings
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <motion.article
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="p-5 rounded-xl glass space-y-3"
        >
          <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Wifi className="w-4 h-4 text-cyan-400" />
            Connection
          </h3>
          <StatRow label="WebSocket" value={connectionState || 'disconnected'} ok={connectionState === 'connected'} />
          <StatRow label="Voice State" value={voiceState || 'idle'} />
          <StatRow label="Auth Mode" value={authStatus?.mode || 'unknown'} />
          <StatRow label="Verified" value={authStatus?.verified ? 'YES' : 'NO'} ok={authStatus?.verified} />
        </motion.article>

        <motion.article
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="p-5 rounded-xl glass space-y-3"
        >
          <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Brain className="w-4 h-4 text-violet-400" />
            Health
          </h3>
          <StatRow label="Microphone" value={healthStatus?.microphone ? 'READY' : 'OFFLINE'} ok={healthStatus?.microphone} />
          <StatRow label="Model Loaded" value={healthStatus?.modelLoaded ? 'YES' : 'NO'} ok={healthStatus?.modelLoaded} />
          <div className="flex flex-wrap gap-2 pt-2">
            {Object.entries(healthStatus?.apis || {}).map(([api, ok]) => (
              <span
                key={api}
                className={cn(
                  "px-2 py-1 rounded-full text-xs font-mono",
                  ok ? "bg-green-400/10 text-green-400" : "bg-amber-400/10 text-amber-400"
                )}
              >
                {api}: {ok ? 'ok' : 'down'}
              </span>
            ))}
            {Object.keys(healthStatus?.apis || {}).length === 0 && (
              <span className="text-xs text-muted-foreground">No API status</span>
            )}
          </div>
        </motion.article>

        <motion.article
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="p-5 rounded-xl glass space-y-3"
        >
          <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <MessageSquare className="w-4 h-4 text-cyan-400" />
            Live Streams
          </h3>
          <div className="space-y-2">
            <div>
              <label className="text-xs text-muted-foreground flex items-center gap-1">
                <Mic className="w-3 h-3" />
                Transcript Stream
              </label>
              <p className="mt-1 text-sm text-foreground/80 font-mono truncate">
                {currentTranscription || 'Waiting for transcript chunks...'}
              </p>
            </div>
            <div>
              <label className="text-xs text-muted-foreground flex items-center gap-1">
                <Brain className="w-3 h-3" />
                Response Stream
              </label>
              <p className="mt-1 text-sm text-foreground/80 font-mono truncate">
                {currentResponse || 'Waiting for response chunks...'}
              </p>
            </div>
          </div>
        </motion.article>
      </div>

      <motion.section
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="rounded-xl glass overflow-hidden"
      >
        <div className="flex items-center justify-between px-5 py-3 border-b border-white/5">
          <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
            <Clock className="w-4 h-4 text-cyan-400" />
            Recent Conversation Events
          </h3>
          <span className="text-xs text-muted-foreground">{recentMessages.length} entries</span>
        </div>
        <div className="max-h-64 overflow-y-auto">
          {recentMessages.length === 0 ? (
            <div className="p-8 text-center">
              <MessageSquare className="w-8 h-8 text-muted-foreground/30 mx-auto mb-2" />
              <p className="text-sm text-muted-foreground">No messages yet. Start by speaking or typing in HUD.</p>
            </div>
          ) : (
            <div className="divide-y divide-white/5">
              {recentMessages.map((message) => (
                <article key={message.id} className="p-4 hover:bg-white/5 transition-colors">
                  <header className="flex items-center justify-between mb-1">
                    <strong className={cn(
                      "text-sm font-medium",
                      message.role === 'assistant' ? "text-cyan-400" : "text-foreground"
                    )}>
                      {message.role === 'assistant' ? 'Jarvis' : 'User'}
                    </strong>
                    <span className="text-xs text-muted-foreground font-mono">
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </span>
                  </header>
                  <p className="text-sm text-muted-foreground line-clamp-2">{message.content}</p>
                  {message.intent && (
                    <small className="text-xs text-violet-400/70 mt-1 block">intent: {message.intent}</small>
                  )}
                </article>
              ))}
            </div>
          )}
        </div>
      </motion.section>
    </div>
  )
}