import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Canvas } from '@react-three/fiber'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Mic, MicOff, Settings, Sun, Moon, Sparkles, Loader2 } from 'lucide-react'
import { cn } from '../lib/utils'
import { useTheme } from '../components/ThemeProvider'
import JarvisReactor from '../components/JarvisReactor'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAppStore } from '../store/appStore'
import { sanitizeAssistantText } from '../utils/textSanitizer'

declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

const QUICK_SUGGESTIONS = [
  "What's the weather today?",
  'Set a reminder for 30 minutes',
  'Open Spotify',
  'Search for latest AI news',
]

export default function MainPage() {
  const navigate = useNavigate()
  const websocket = useWebSocket()
  const { theme, toggleTheme } = useTheme()
  const addToast = useAppStore((state) => state.addToast)
  const connectionState = useAppStore((state) => state.connectionState)
  const setVoiceStateStore = useAppStore((state) => state.setVoiceState)
  const messages = useAppStore((state) => state.messages)
  const addMessage = useAppStore((state) => state.addMessage)
  const alwaysOnSpeaker = useAppStore((state) => state.alwaysOnSpeaker)
  const setAlwaysOnSpeaker = useAppStore((state) => state.setAlwaysOnSpeaker)

  const [voiceState, setVoiceState] = useState('idle')
  const [liveUserText, setLiveUserText] = useState('')
  const [liveAssistantText, setLiveAssistantText] = useState('')
  const [displayedAssistantText, setDisplayedAssistantText] = useState('')
  const [isTapBusy, setIsTapBusy] = useState(false)
  const [typedText, setTypedText] = useState('')
  const [latencyMs, setLatencyMs] = useState<number | null>(null)
  const [audioLevels, setAudioLevels] = useState<number[]>([])

  const isBusy = ['wake_detected', 'listening', 'transcribing', 'thinking', 'speaking'].includes(voiceState)

  const connectionMeta = useMemo(() => {
    if (connectionState === 'connected') return { icon: '●', text: 'Online', className: 'text-green-500' }
    if (connectionState === 'reconnecting' || connectionState === 'connecting') return { icon: '○', text: 'Connecting', className: 'text-amber-500' }
    return { icon: '✕', text: 'Offline', className: 'text-red-500' }
  }, [connectionState])

  const liveUserTextRef = useRef('')
  const liveAssistantTextRef = useRef('')
  const inputRef = useRef(null)
  const manualSessionActiveRef = useRef(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => { liveUserTextRef.current = liveUserText }, [liveUserText])
  useEffect(() => { liveAssistantTextRef.current = liveAssistantText }, [liveAssistantText])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth'
      })
    }
  }, [messages, liveAssistantText, liveUserText])

  // Reset displayed text when live text is cleared
  if (!liveAssistantText.trim() && displayedAssistantText !== '') {
    setDisplayedAssistantText('')
  }
  // Sync if animation is finished or exceeds target
  if (liveAssistantText.trim() && displayedAssistantText.length >= liveAssistantText.length && displayedAssistantText !== liveAssistantText) {
    setDisplayedAssistantText(liveAssistantText)
  }

  useEffect(() => {
    if (!liveAssistantText.trim() || displayedAssistantText.length >= liveAssistantText.length) return

    const timer = setInterval(() => {
      setDisplayedAssistantText(prev => {
        const nextLen = Math.min(prev.length + Math.floor(Math.random() * 2) + 1, liveAssistantText.length)
        return liveAssistantText.slice(0, nextLen)
      })
    }, 30)
    return () => clearInterval(timer)
  }, [liveAssistantText, displayedAssistantText.length])

  const finalizeAssistantStreaming = useCallback(() => {
    const text = sanitizeAssistantText(liveAssistantTextRef.current)
    if (text) {
      addMessage('assistant', text, { source: 'voice' })
      setLiveAssistantText('')
      setDisplayedAssistantText('')
    }
  }, [addMessage])
  const handleTextSubmit = (e: FormEvent) => {
    if (e) e.preventDefault()
    if (!typedText.trim()) return
    sendTextCommand(typedText)
    setTypedText('')
  }

  const sendTextCommand = (text: string) => {
    const command = String(text || '').trim()
    if (!command) return
    const sent = websocket.sendMessage({ type: 'user_command', payload: { text: command, source: 'keyboard' } })
    if (!sent) {
      addToast({ type: 'warning', title: 'Backend not connected', message: 'Unable to send command.' })
      return
    }
    addMessage('user', command, { source: 'keyboard' })
  }

  const handleMicClick = () => {
    if (isBusy) {
      // Toggle OFF: send interrupt to stop current voice session
      const sent = websocket.sendMessage({ type: 'interrupt', payload: { source: 'tap_to_speak' } })
      if (sent) {
        manualSessionActiveRef.current = false
        setIsTapBusy(false)
      }
      return
    }

    // Toggle ON: start listening
    manualSessionActiveRef.current = true
    setIsTapBusy(true)
    const sent = websocket.sendMessage({ type: 'start_listening', payload: { source: 'tap_to_speak' } })
    if (!sent) {
      manualSessionActiveRef.current = false
      setIsTapBusy(false)
      addToast({ type: 'warning', title: 'Not connected', message: 'Backend WebSocket is not connected yet.' })
    }
  }

  useEffect(() => {
    if (!websocket) return
    const unsubscribers = [
      websocket.subscribe('voice_state_change', (payload: any) => {
        const next = payload?.state || 'idle'
        setVoiceState(next)
        setVoiceStateStore(next)
        ;(window as any).jarvis?.tray?.setState?.(next)
        if (next === 'idle' || next === 'error') {
          manualSessionActiveRef.current = false
          setIsTapBusy(false)
        }
        if (next === 'thinking' || next === 'speaking') {
          setIsTapBusy(false)
        }
      }),
      websocket.subscribe('transcript_chunk', (payload: any) => {
        const text = payload?.text || payload?.chunk || ''
        if (!text) return
        if (payload?.is_final) {
          const finalText = payload.text || liveUserTextRef.current || text
          if (finalText) {
            addMessage('user', finalText, { source: 'voice' })
            setLiveUserText('')
          }
          return
        }
        if (payload?.text) setLiveUserText(payload.text)
        else if (payload?.chunk) setLiveUserText(prev => `${prev}${payload.chunk}`)
      }),
      websocket.subscribe('tts_start', () => {
        setLiveAssistantText('')
        setVoiceState('speaking')
      }),
      websocket.subscribe('assistant_response_chunk', (payload: any) => {
        const chunk = sanitizeAssistantText(payload?.text_chunk || '')
        if (!chunk) return
        setLiveAssistantText(prev => `${prev}${chunk}`)
      }),
      websocket.subscribe('tts_end', (payload: any) => {
        if (payload?.duration_ms) setLatencyMs(Math.round(Number(payload.duration_ms)))
        finalizeAssistantStreaming()
        
        // Only reset to idle if we are currently speaking.
        // If we are already listening (due to interrupt), don't reset.
        setVoiceState(prev => {
          if (prev === 'speaking') {
            setVoiceStateStore('idle')
            return 'idle'
          }
          return prev
        })
      }),
      websocket.subscribe('audio_level', (payload: any) => {
        setAudioLevels(Array.isArray(payload?.levels) ? payload.levels : [])
      }),
      websocket.subscribe('error', (payload: any) => {
        setVoiceState('error')
        setVoiceStateStore('error')
        addToast({ type: 'warning', title: payload?.code || 'Error', message: payload?.message })
      }),
    ]
    return () => unsubscribers.forEach(un => un?.())
  }, [addMessage, addToast, setVoiceStateStore, websocket, finalizeAssistantStreaming])

  const hasMessages = messages.length > 0 || !!liveUserText || !!liveAssistantText

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-screen flex flex-col relative overflow-hidden"
    >
      {/* Background Reactor Layer */}
      <div className="fixed inset-0 pointer-events-none flex items-center justify-center opacity-30 z-0 overflow-hidden">
        <div className="w-[120%] h-[120%] sm:w-full sm:h-full max-w-5xl">
          <Canvas camera={{ position: [0, 0, 6] }}>
            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={1} />
            <JarvisReactor state={voiceState.toUpperCase()} audioLevel={Math.max(...audioLevels, 0)} />
          </Canvas>
        </div>
      </div>

      {/* Content Layer (Foreground) */}
      <div className="relative z-10 h-full flex flex-col">
        {/* Header */}
        <motion.header 
          initial={{ y: -20, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          className="flex items-center justify-between px-6 py-6"
        >
          <div>
            <motion.h1 
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              className="text-4xl font-black tracking-tighter"
            >
              <span className="text-gradient">JARVIS</span>
            </motion.h1>
            <div className="flex items-center gap-2 mt-1">
              <span className="h-[1px] w-8 bg-primary/40" />
              <p className="text-[10px] uppercase tracking-[0.3em] text-muted-foreground/80 font-mono">System OS // HUD_V1</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-4 px-4 py-2 rounded-2xl bg-black/20 border border-white/5 backdrop-blur-md">
              <span className={cn("flex items-center gap-2 text-[10px] font-mono tracking-widest", connectionMeta.className)}>
                <span className="w-1 h-1 rounded-full bg-current animate-pulse shadow-[0_0_8px_currentColor]" />
                {connectionMeta.text}
              </span>
              {latencyMs !== null && (
                <>
                  <span className="h-3 w-[1px] bg-white/10" />
                  <span className="text-[10px] font-mono tracking-widest text-cyan-400/80">
                    LATENCY: {latencyMs}MS
                  </span>
                </>
              )}
            </div>
            <motion.button
              whileHover={{ scale: 1.05, backgroundColor: 'rgba(255,255,255,0.1)' }}
              whileTap={{ scale: 0.95 }}
              onClick={toggleTheme}
              className="p-3 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xl transition-all"
            >
              {theme === 'dark' ? <Sun size={20} className="text-foreground/80" /> : <Moon size={20} className="text-foreground/80" />}
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.05, backgroundColor: 'rgba(255,255,255,0.1)' }}
              whileTap={{ scale: 0.95 }}
              onClick={() => navigate('/settings')}
              className="p-3 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-xl transition-all"
            >
              <Settings size={20} className="text-foreground/80" />
            </motion.button>
          </div>
        </motion.header>

        {/* Chat / Conversation Area */}
        <main className="flex-1 flex flex-col items-center relative overflow-hidden">
          <section className="w-full max-w-4xl h-full flex flex-col justify-end pb-4 overflow-hidden relative">
            <div className="flex-1 overflow-y-auto no-scrollbar scroll-smooth px-6 py-8" ref={scrollRef}>
              <AnimatePresence mode="popLayout">
                {!hasMessages ? (
                  <motion.div
                    key="suggestions"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="h-full flex flex-col items-center justify-center gap-8"
                  >
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-2xl">
                      {QUICK_SUGGESTIONS.map((chip, i) => (
                        <motion.button
                          key={chip}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: 0.1 * i }}
                          whileHover={{ scale: 1.02, x: 5 }}
                          whileTap={{ scale: 0.98 }}
                          onClick={() => sendTextCommand(chip)}
                          className={cn(
                            "group flex items-center justify-between p-5 rounded-2xl text-left",
                            "bg-white/5 hover:bg-cyan-500/10 border border-white/20 hover:border-cyan-500/60",
                            "backdrop-blur-md transition-all duration-500 shadow-lg"
                          )}
                        >
                          <span className="text-sm font-medium text-foreground/80 group-hover:text-cyan-400">{chip}</span>
                          <Sparkles size={14} className="text-white/20 group-hover:text-cyan-400 transition-colors" />
                        </motion.button>
                      ))}
                    </div>
                  </motion.div>
                ) : (
                  <div className="flex flex-col gap-8 min-h-full justify-end">
                    {messages.map((msg: any) => (
                      <motion.div
                        key={msg.id}
                        initial={{ opacity: 0, y: 20, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        transition={{ duration: 0.4, ease: "easeOut" }}
                        className={cn(
                          "max-w-[85%] rounded-2xl px-6 py-4 border shadow-2xl transition-colors duration-300",
                          msg.role === 'user' 
                            ? "self-end bg-cyan-600/10 border-cyan-500/40 text-right backdrop-blur-md"
                            : "self-start bg-white/5 border-white/20 text-left backdrop-blur-xl"
                        )}
                      >
                         {msg.role !== 'user' && (
                           <div className="flex items-center gap-2 mb-2">
                             <div className="w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_8px_#22d3ee]" />
                             <span className="text-[10px] font-black tracking-[0.2em] text-cyan-400/80 uppercase">Jarvis Analysis</span>
                           </div>
                         )}
                        <p className={cn(
                          "leading-relaxed",
                          msg.role === 'user' ? "text-base text-foreground/90" : "text-lg text-foreground font-medium"
                        )}>
                          {msg.content}
                        </p>
                      </motion.div>
                    ))}
                    
                    {liveUserText && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="self-end max-w-[85%] rounded-2xl px-6 py-4 border border-cyan-500/50 bg-cyan-500/10 backdrop-blur-md shadow-xl"
                      >
                        <p className="text-base text-cyan-100/90">{liveUserText}<span className="cursor-blink ml-1 text-cyan-400 font-bold">_</span></p>
                      </motion.div>
                    )}

                    {voiceState === 'thinking' && !liveAssistantText && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="self-start flex items-center gap-4 px-6 py-4 border border-white/20 backdrop-blur-xl rounded-2xl bg-white/5 shadow-2xl"
                      >
                        <div className="flex gap-1">
                          {[0, 1, 2].map(i => (
                            <motion.div 
                              key={i}
                              animate={{ scale: [1, 1.5, 1], opacity: [0.3, 1, 0.3] }}
                              transition={{ repeat: Infinity, duration: 1, delay: i * 0.2 }}
                              className="w-1.5 h-1.5 rounded-full bg-cyan-400"
                            />
                          ))}
                        </div>
                        <span className="text-[10px] font-black tracking-[0.3em] uppercase text-muted-foreground">Synthesizing Neural Response</span>
                      </motion.div>
                    )}

                    {liveAssistantText && (
                      <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="self-start w-full"
                      >
                        <div className="max-w-[95%] rounded-3xl px-8 py-8 border border-white/20 bg-black/60 backdrop-blur-xl shadow-[0_0_50px_rgba(0,0,0,0.5)] relative overflow-hidden group">
                          <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-cyan-500 to-transparent opacity-70" />
                          <div className="flex items-center gap-3 mb-4">
                             <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_12px_#22d3ee]" />
                             <span className="text-[11px] font-black tracking-[0.4em] text-cyan-400 uppercase">Incoming Transmission</span>
                          </div>
                          <p className="text-2xl sm:text-3xl leading-[1.4] font-semibold text-foreground tracking-tight text-balance">
                            {displayedAssistantText || liveAssistantText}
                            <span className="cursor-blink ml-2 text-cyan-400 shadow-[0_0_10px_#22d3ee]">▍</span>
                          </p>
                        </div>
                      </motion.div>
                    )}
                  </div>
                )}
              </AnimatePresence>
            </div>
          </section>
        </main>

        {/* Input Area */}
        <footer className="w-full max-w-3xl mx-auto px-4 pb-8 pt-4">
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="flex items-center gap-4 p-4 rounded-3xl border border-white/10 shadow-2xl backdrop-blur-3xl bg-black/20"
          >
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={handleMicClick}
              disabled={connectionState !== 'connected'}
              className={cn(
                "w-14 h-14 rounded-2xl flex items-center justify-center transition-all duration-300 shadow-lg",
                isBusy 
                  ? "bg-red-500 text-white hover:bg-red-600 animate-pulse"
                  : "bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/30 text-cyan-400",
                connectionState !== 'connected' && "opacity-40 cursor-not-allowed"
              )}
            >
              {isBusy ? <MicOff size={24} /> : <Mic size={24} />}
            </motion.button>

            <form
              onSubmit={handleTextSubmit}
              className="flex-1 flex items-center gap-3 px-2"
            >
              <input
                ref={inputRef}
                value={typedText}
                onChange={(e) => setTypedText(e.target.value)}
                placeholder="Ask me anything..."
                className="flex-1 bg-transparent border-none outline-none text-foreground placeholder:text-muted-foreground/50 text-lg py-2"
              />
              <motion.button
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                type="submit"
                disabled={!typedText.trim()}
                className={cn(
                  "p-3.5 rounded-2xl transition-all duration-300 shadow-xl",
                  "bg-gradient-to-br from-cyan-500 to-blue-600 text-white",
                  "hover:from-cyan-400 hover:to-blue-500",
                  "disabled:opacity-20 disabled:grayscale"
                )}
              >
                <Send size={20} />
              </motion.button>
            </form>

            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setAlwaysOnSpeaker(!alwaysOnSpeaker)}
              className={cn(
                "hidden sm:flex items-center gap-3 px-5 py-3 rounded-2xl text-sm font-bold transition-all duration-300",
                alwaysOnSpeaker 
                  ? "bg-cyan-500/20 border border-cyan-500/40 text-cyan-400 shadow-[0_0_15px_rgba(34,211,238,0.2)]"
                  : "bg-white/5 border border-white/10 text-muted-foreground/60"
              )}
            >
              <div className="flex items-center gap-2">
                <span className={cn("w-2 h-2 rounded-full", alwaysOnSpeaker ? "bg-cyan-400 animate-pulse shadow-[0_0_8px_#22d3ee]" : "bg-white/20")} />
                <span className="tracking-widest">{alwaysOnSpeaker ? 'LIVE' : 'AUTO'}</span>
              </div>
            </motion.button>
          </motion.div>
        </footer>
      </div>
    </motion.div>
  )
}