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

  const supportsLocalSpeech = useMemo(() => {
    if (typeof window === 'undefined') return false
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition)
  }, [])

  const isBusy = ['wake_detected', 'listening', 'transcribing', 'thinking', 'speaking'].includes(voiceState)

  const connectionMeta = useMemo(() => {
    if (connectionState === 'connected') return { icon: '●', text: 'Online', className: 'text-green-500' }
    if (connectionState === 'reconnecting' || connectionState === 'connecting') return { icon: '○', text: 'Connecting', className: 'text-amber-500' }
    return { icon: '✕', text: 'Offline', className: 'text-red-500' }
  }, [connectionState])

  const liveUserTextRef = useRef('')
  const liveAssistantTextRef = useRef('')
  const prevVoiceStateRef = useRef('idle')
  const localSpeechRef = useRef<any>(null)
  const localSpeechActiveRef = useRef(false)
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

  const stopLocalSpeechPreview = useCallback(() => {
    localSpeechActiveRef.current = false
    const recognition = localSpeechRef.current as any
    if (!recognition) return
    try { recognition.stop() } catch { /* ignore */ }
  }, [])

  const startLocalSpeechPreview = useCallback(() => {
    if (!supportsLocalSpeech || localSpeechActiveRef.current) return
    let recognition = localSpeechRef.current as any
    if (!recognition) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      if (!SpeechRecognition) return
      recognition = new SpeechRecognition()
      recognition.lang = 'en-US'
      recognition.continuous = true
      recognition.interimResults = true
      localSpeechRef.current = recognition
    }

    recognition.onresult = (event: any) => {
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i]
        const text = result?.[0]?.transcript || ''
        if (result?.isFinal) {
          if (text.trim()) setLiveUserText(text.trim())
        } else {
          interim += text
        }
      }
      if (interim.trim()) setLiveUserText(interim.trim())
    }
    recognition.onerror = () => { localSpeechActiveRef.current = false }
    recognition.onend = () => {
      if (!localSpeechActiveRef.current) return
      try { (recognition as any).start() } catch { localSpeechActiveRef.current = false }
    }
    localSpeechActiveRef.current = true
    try { (recognition as any).start() } catch { localSpeechActiveRef.current = false }
  }, [supportsLocalSpeech])

  const finalizeAssistantStreaming = useCallback(() => {
    const text = sanitizeAssistantText(liveAssistantTextRef.current)
    if (text) {
      addMessage('assistant', text, { source: 'voice' })
      setLiveAssistantText('')
      setDisplayedAssistantText('')
    }
  }, [addMessage])

  useEffect(() => {
    const prev = prevVoiceStateRef.current
    prevVoiceStateRef.current = voiceState
    if (alwaysOnSpeaker && prev === 'speaking' && voiceState === 'idle' && connectionState === 'connected') {
      const timer = setTimeout(() => {
        if (websocket.sendMessage({ type: 'start_listening', payload: { source: 'always_on' } })) {
          manualSessionActiveRef.current = true
          startLocalSpeechPreview()
        }
      }, 750)
      return () => clearTimeout(timer)
    }
  }, [voiceState, alwaysOnSpeaker, connectionState, websocket, startLocalSpeechPreview])

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
      websocket.sendMessage({ type: 'interrupt', payload: {} })
      manualSessionActiveRef.current = false
      stopLocalSpeechPreview()
      return
    }
    manualSessionActiveRef.current = true
    setIsTapBusy(true)
    const sent = websocket.sendMessage({ type: 'start_listening', payload: { source: 'tap_to_speak' } })
    if (!sent) {
      manualSessionActiveRef.current = false
      setIsTapBusy(false)
      stopLocalSpeechPreview()
      addToast({ type: 'warning', title: 'Not connected', message: 'Backend WebSocket is not connected yet.' })
    } else {
      startLocalSpeechPreview()
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
          stopLocalSpeechPreview()
        }
        if (next === 'thinking' || next === 'speaking') {
          stopLocalSpeechPreview()
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
        setVoiceState('idle')
        setVoiceStateStore('idle')
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
  }, [addMessage, addToast, setVoiceStateStore, websocket, stopLocalSpeechPreview, finalizeAssistantStreaming])

  const hasMessages = messages.length > 0 || !!liveUserText || !!liveAssistantText

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="min-h-screen flex flex-col"
    >
      {/* Header */}
      <motion.header 
        initial={{ y: -20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        className="flex items-center justify-between px-3 sm:px-4 py-2"
      >
        <div>
          <motion.h1 
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            className="text-3xl font-bold tracking-tight"
          >
            <span className="text-gradient">Jarvis</span>
          </motion.h1>
          <p className="text-sm text-muted-foreground">Advanced Voice Assistant</p>
        </div>
        <div className="flex items-center gap-2">
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={toggleTheme}
            className={cn(
              "p-2 rounded-full transition-colors",
              "bg-white/5 hover:bg-white/10 border border-white/10",
              "backdrop-blur-xl"
            )}
          >
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </motion.button>
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => navigate('/settings')}
            className={cn(
              "p-2 rounded-full transition-colors",
              "bg-white/5 hover:bg-white/10 border border-white/10",
              "backdrop-blur-xl"
            )}
          >
            <Settings size={18} />
          </motion.button>
        </div>
      </motion.header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 sm:px-6 lg:px-8">
           <motion.div
             initial={{ scale: 0.8, opacity: 0 }}
             animate={{ scale: 1, opacity: 1 }}
             transition={{ delay: 0.1 }}
             className="w-full max-w-2xl h-[300px] sm:h-[400px] relative"
           >
          <Canvas camera={{ position: [0, 0, 6] }}>
            <ambientLight intensity={0.5} />
            <pointLight position={[10, 10, 10]} intensity={1} />
            <JarvisReactor state={voiceState.toUpperCase()} audioLevel={Math.max(...audioLevels, 0)} />
          </Canvas>
        </motion.div>

        {/* Status Pills */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
          className="flex items-center gap-3 mt-4"
        >
          <span className={cn("flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-mono bg-white/5 border border-white/10 backdrop-blur-xl", connectionMeta.className)}>
            <span className="w-1.5 h-1.5 rounded-full bg-current animate-pulse" />
            {connectionMeta.text}
          </span>
          {latencyMs !== null && (
            <span className="px-3 py-1.5 rounded-full text-xs font-mono bg-white/5 border border-white/10 backdrop-blur-xl">
              <Sparkles size={12} className="inline mr-1" />
              {latencyMs}ms
            </span>
          )}
        </motion.div>
      </main>

      {/* Chat Area */}
      <section className="flex-1 w-full max-w-2xl mx-auto px-4 flex flex-col min-h-0">
         <AnimatePresence mode="wait">
            {!hasMessages ? (
              <motion.div
                key="suggestions"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex flex-wrap justify-center gap-4 py-8"
              >
                {QUICK_SUGGESTIONS.map((chip, i) => (
                  <motion.button
                    key={chip}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.1 * i }}
                    whileHover={{ scale: 1.05, y: -2 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => sendTextCommand(chip)}
                    className={cn(
                      "px-6 py-3 rounded-xl text-sm font-medium",
                      "bg-white/5 hover:bg-white/10 border border-white/20",
                      "backdrop-blur-xl transition-all duration-300",
                      "hover:glow-cyan hover:border-cyan-500/50"
                    )}
                  >
                    {chip}
                  </motion.button>
                ))}
              </motion.div>
            ) : (
              <motion.div
                key="messages"
                ref={scrollRef}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex-1 flex flex-col gap-4 p-4 overflow-y-auto no-scrollbar scroll-smooth"
              >
                {messages.slice(-10).map((msg: any, i: number) => (
                  <motion.div
                    key={msg.id}
                    layout
                    initial={{ opacity: 0, x: msg.role === 'user' ? 20 : -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.03, duration: 0.5 }}
                    className={cn(
                      "max-w-[85%] rounded-2xl px-5 py-3 border backdrop-blur-xl transition-all duration-300",
                      msg.role === 'user' 
                        ? "self-end bg-cyan-500/10 border-cyan-500/10 shadow-sm"
                        : "self-start bg-white/5 border-white/5 shadow-sm"
                    )}
                  >
                    <div className="flex flex-col">
                      <p className="text-sm leading-relaxed">{msg.content}</p>
                      {msg.meta && Object.keys(msg.meta).length > 0 && (
                        <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                          {Object.entries(msg.meta).map(([key, value]) => (
                            <span key={key} className="flex items-center gap-1">
                              <span className="w-1 h-1 rounded-full bg-muted-foreground/50" />
                              <span className="whitespace-nowrap">{(value as React.ReactNode)}</span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </motion.div>
                ))}
                {liveUserText && (
                  <motion.div
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="self-end max-w-[85%] rounded-2xl px-5 py-3 border border-white/5 backdrop-blur-xl"
                    style={{ backgroundColor: 'color-mix(in srgb, var(--color-background-muted), transparent 60%)' }}
                  >
                    <div className="flex flex-col">
                      <p className="text-sm">{liveUserText}</p>
                    </div>
                    <span className="cursor-blink ml-1">▍</span>
                  </motion.div>
                )}
                {voiceState === 'thinking' && !liveAssistantText && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="self-center flex items-center gap-3 px-4 py-2 border border-white/5 backdrop-blur-xl rounded-full"
                    style={{ backgroundColor: 'color-mix(in srgb, var(--color-background-muted), transparent 60%)' }}
                  >
                    <Loader2 size={14} className="animate-spin" />
                    <span className="text-sm">Thinking...</span>
                  </motion.div>
                )}
                {liveAssistantText && (
                  <motion.div
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="self-center max-w-[85%] rounded-2xl px-5 py-3 border border-white/5 backdrop-blur-xl"
                    style={{ backgroundColor: 'color-mix(in srgb, var(--color-background-muted), transparent 60%)' }}
                  >
                    <div className="flex flex-col">
                      <p className="text-lg leading-relaxed">{displayedAssistantText || liveAssistantText}</p>
                    </div>
                    <span className="cursor-blink ml-1">▍</span>
                  </motion.div>
                )}
              </motion.div>
            )}
         </AnimatePresence>
       </section>

       {/* Input Area */}
       <footer className="w-full max-w-xl mx-auto px-4 pb-8">
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="flex items-center gap-4 p-4 rounded-2xl border border-white/5 shadow-2xl backdrop-blur-3xl"
            style={{ backgroundColor: 'color-mix(in srgb, var(--color-background-muted), transparent 60%)' }}
          >
             <motion.button
               whileHover={{ scale: 1.1 }}
               whileTap={{ scale: 0.9 }}
               onClick={handleMicClick}
               disabled={isTapBusy && !isBusy}
                className={cn(
                  "w-14 h-14 rounded-full flex items-center justify-center transition-all duration-300",
                  isBusy 
                    ? "bg-red-500 text-white shadow-lg hover:bg-red-600"
                    : "bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/30 text-cyan-400"
                )}
             >
               {isBusy ? <MicOff size={22} className="text-white" /> : <Mic size={22} className="text-cyan-400" />}
             </motion.button>

            <form
              onSubmit={handleTextSubmit}
              className="flex-1 flex items-center gap-3"
            >
              <input
                ref={inputRef}
                value={typedText}
                onChange={(e) => setTypedText(e.target.value)}
                placeholder="How can I help you today?"
                className="flex-1 bg-transparent border-none outline-none text-foreground placeholder:text-muted-foreground"
                style={{ fontSize: '1rem' }}
              />
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                type="submit"
                disabled={!typedText.trim()}
                className={cn(
                  "p-3 rounded-xl",
                  "bg-gradient-to-r from-cyan-500 to-violet-500 text-white",
                  "hover:from-cyan-400 hover:to-violet-400",
                  "transition-all duration-300",
                  "shadow-lg",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
                )}
              >
                <Send size={20} className="text-white" />
              </motion.button>
            </form>

            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setAlwaysOnSpeaker(!alwaysOnSpeaker)}
              className={cn(
                "flex items-center gap-3 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300",
                alwaysOnSpeaker 
                  ? "bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/30 text-cyan-400"
                  : "bg-white/5 hover:bg-white/10 border border-white/10"
              )}
            >
              <motion.div className="flex items-center gap-1">
                <span className={cn("w-2.5 h-2.5 rounded-full", alwaysOnSpeaker ? "bg-cyan-400 animate-pulse" : "bg-white/30")} />
                <span className="whitespace-nowrap">{alwaysOnSpeaker ? 'LIVE' : 'AUTO'}</span>
              </motion.div>
            </motion.button>
          </motion.div>
        </footer>
     </motion.div>
  )
}