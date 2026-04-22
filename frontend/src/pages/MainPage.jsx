import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Canvas } from '@react-three/fiber'
import { Activity, Mic, MicOff, SendHorizonal, Settings2, Sparkles } from 'lucide-react'
import GeminiBlob from '../components/GeminiBlob'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAppStore } from '../store/appStore'
import { BACKEND_HEALTH_URL, BACKEND_WS_URL } from '../utils/constants'
import { sanitizeAssistantText } from '../utils/textSanitizer'

const QUICK_SUGGESTIONS = [
  "What's the weather today?",
  'Set a reminder for 30 minutes',
  'Open Spotify',
  'Search for latest AI news',
]

export default function MainPage() {
  const navigate = useNavigate()
  const websocket = useWebSocket()
  const setMuted = useAppStore((state) => state.setMuted)
  const addToast = useAppStore((state) => state.addToast)
  const connectionState = useAppStore((state) => state.connectionState)
  const setVoiceStateStore = useAppStore((state) => state.setVoiceState)
  const messages = useAppStore((state) => state.messages)
  const addMessage = useAppStore((state) => state.addMessage)
  const healthStatus = useAppStore((state) => state.healthStatus)
  const browserMicPermission = useAppStore((state) => state.browserMicPermission)
  const alwaysOnSpeaker = useAppStore((state) => state.alwaysOnSpeaker)
  const setAlwaysOnSpeaker = useAppStore((state) => state.setAlwaysOnSpeaker)

  const [voiceState, setVoiceState] = useState('idle')
  const [liveUserText, setLiveUserText] = useState('')
  const [liveAssistantText, setLiveAssistantText] = useState('')
  const [displayedAssistantText, setDisplayedAssistantText] = useState('')
  const [isTapBusy, setIsTapBusy] = useState(false)
  const [typedText, setTypedText] = useState('')
  const [connectionHint, setConnectionHint] = useState('')
  const [latencyMs, setLatencyMs] = useState(null)
  const [audioLevels, setAudioLevels] = useState([])
  const [healthProbe, setHealthProbe] = useState({
    checked: false,
    reachable: true,
    healthy: true,
    message: '',
  })

  const scrollRef = useRef(null)
  const connectSinceRef = useRef(0)
  const manualSessionActiveRef = useRef(false)
  const liveUserTextRef = useRef('')
  const liveAssistantTextRef = useRef('')
  const lastUserFinalRef = useRef('')
  const lastAssistantFinalRef = useRef('')
  const localSpeechRef = useRef(null)
  const localSpeechActiveRef = useRef(false)
  const prevVoiceStateRef = useRef('idle')
  const inputRef = useRef(null)

  const supportsLocalSpeech = useMemo(() => {
    if (typeof window === 'undefined') return false
    return !!(window.SpeechRecognition || window.webkitSpeechRecognition)
  }, [])

  const canShowWaveform = voiceState === 'listening' || voiceState === 'speaking'
  const isBusy =
    voiceState === 'wake_detected' ||
    voiceState === 'listening' ||
    voiceState === 'transcribing' ||
    voiceState === 'thinking' ||
    voiceState === 'speaking'

  const connectionMeta = useMemo(() => {
    if (connectionState === 'connected') {
      return { icon: '●', text: 'Connected', className: 'connected' }
    }
    if (connectionState === 'reconnecting') {
      return { icon: '○', text: 'Reconnecting', className: 'connecting' }
    }
    if (connectionState === 'connecting') {
      return { icon: '○', text: 'Connecting', className: 'connecting' }
    }
    return { icon: '✕', text: 'Disconnected', className: 'disconnected' }
  }, [connectionState])

  const micMeta = useMemo(() => {
    if (browserMicPermission === 'denied') {
      return { text: 'Mic blocked', className: 'disconnected' }
    }

    if (healthStatus?.microphone) {
      return { text: 'Mic ready', className: 'connected' }
    }

    if (connectionState === 'disconnected' || connectionState === 'reconnecting') {
      return { text: 'Mic unknown', className: 'connecting' }
    }

    return { text: 'Mic offline', className: 'disconnected' }
  }, [browserMicPermission, connectionState, healthStatus?.microphone])

  useEffect(() => {
    liveUserTextRef.current = liveUserText
  }, [liveUserText])

  useEffect(() => {
    liveAssistantTextRef.current = liveAssistantText
  }, [liveAssistantText])

  useEffect(() => {
    if (!liveAssistantText.trim()) {
      setDisplayedAssistantText('')
      return
    }

    const incomingWords = liveAssistantText.trim().split(/\s+/)
    const shownWords = displayedAssistantText.trim() ? displayedAssistantText.trim().split(/\s+/) : []

    if (shownWords.length >= incomingWords.length) {
      setDisplayedAssistantText(liveAssistantText)
      return
    }

    let index = shownWords.length
    const timer = setInterval(() => {
      index += 1
      setDisplayedAssistantText(incomingWords.slice(0, index).join(' '))
      if (index >= incomingWords.length) {
        clearInterval(timer)
      }
    }, 38)

    return () => clearInterval(timer)
  }, [liveAssistantText, displayedAssistantText])

  // Always-on speaker: auto-listen after speaking ends
  useEffect(() => {
    const prev = prevVoiceStateRef.current
    prevVoiceStateRef.current = voiceState

    if (
      alwaysOnSpeaker &&
      prev === 'speaking' &&
      voiceState === 'idle' &&
      connectionState === 'connected'
    ) {
      // Small delay to let the pipeline settle
      const timer = setTimeout(() => {
        const sent = websocket.sendMessage({
          type: 'start_listening',
          payload: { source: 'always_on' },
        })
        if (sent) {
          manualSessionActiveRef.current = true
          startLocalSpeechPreview()
        }
      }, 600)
      return () => clearTimeout(timer)
    }
  }, [voiceState, alwaysOnSpeaker, connectionState, websocket])

  const finalizeAssistantStreaming = () => {
    const text = sanitizeAssistantText(liveAssistantTextRef.current)
    if (text && text !== lastAssistantFinalRef.current) {
      addMessage('assistant', text, { source: 'voice' })
      lastAssistantFinalRef.current = text
    }
    setLiveAssistantText('')
    setDisplayedAssistantText('')
  }

  const stopLocalSpeechPreview = () => {
    localSpeechActiveRef.current = false
    const recognition = localSpeechRef.current
    if (!recognition) return
    try {
      recognition.stop()
    } catch {
      // noop
    }
  }

  const startLocalSpeechPreview = () => {
    if (!supportsLocalSpeech || localSpeechActiveRef.current) return

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) return

    const recognition = localSpeechRef.current || new SpeechRecognition()
    recognition.lang = 'en-US'
    recognition.continuous = true
    recognition.interimResults = true

    recognition.onresult = (event) => {
      let interim = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i]
        const text = result?.[0]?.transcript || ''
        if (result?.isFinal) {
          if (text.trim()) {
            setLiveUserText(text.trim())
          }
        } else {
          interim += text
        }
      }

      if (interim.trim()) {
        setLiveUserText(interim.trim())
      }
    }

    recognition.onerror = () => {
      localSpeechActiveRef.current = false
    }

    recognition.onend = () => {
      if (!localSpeechActiveRef.current) return
      try {
        recognition.start()
      } catch {
        localSpeechActiveRef.current = false
      }
    }

    localSpeechRef.current = recognition
    localSpeechActiveRef.current = true

    try {
      recognition.start()
    } catch {
      localSpeechActiveRef.current = false
    }
  }

  const sendTextCommand = (text) => {
    const command = String(text || '').trim()
    if (!command) return

    const sent = websocket.sendMessage({
      type: 'user_command',
      payload: {
        text: command,
        source: 'keyboard',
      },
    })

    if (!sent) {
      addToast({
        type: 'warning',
        title: 'Backend not connected',
        message: 'Unable to send command. Please check connection.',
      })
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
    const sent = websocket.sendMessage({
      type: 'start_listening',
      payload: { source: 'tap_to_speak' },
    })

    if (!sent) {
      manualSessionActiveRef.current = false
      setIsTapBusy(false)
      stopLocalSpeechPreview()
      addToast({
        type: 'warning',
        title: 'Not connected',
        message: 'Backend WebSocket is not connected yet.',
      })
    } else {
      startLocalSpeechPreview()
    }
  }

  // WebSocket event subscriptions
  useEffect(() => {
    if (!websocket) return

    const unsubscribers = [
      websocket.subscribe('voice_state_change', (payload) => {
        const next = payload?.state || 'idle'

        setVoiceState(next)
        setVoiceStateStore(next)
        window.jarvis?.tray?.setState?.(next)

        if (next === 'wake_detected' || next === 'listening') {
          manualSessionActiveRef.current = true
        }

        if (next === 'idle' || next === 'error') {
          manualSessionActiveRef.current = false
          setIsTapBusy(false)
          stopLocalSpeechPreview()
        }

        if (next === 'wake_detected' || next === 'listening' || next === 'transcribing' || next === 'thinking' || next === 'speaking') {
          setIsTapBusy(false)
        }

        if (next === 'listening') {
          startLocalSpeechPreview()
        }

        if (next === 'thinking' || next === 'speaking') {
          stopLocalSpeechPreview()
        }
      }),
      websocket.subscribe('transcript_chunk', (payload) => {
        const text = payload?.text || payload?.chunk || ''
        if (!text) return

        if (payload?.is_final) {
          const finalText = payload.text || liveUserTextRef.current || text
          if (!finalText || finalText === lastUserFinalRef.current) {
            setLiveUserText('')
            return
          }

          setLiveUserText('')
          addMessage('user', finalText, { source: 'voice' })
          lastUserFinalRef.current = finalText
          return
        }

        if (payload?.text) {
          setLiveUserText(payload.text)
        } else if (payload?.chunk) {
          setLiveUserText((prev) => `${prev}${payload.chunk}`)
        }
      }),
      websocket.subscribe('transcription_result', (payload) => {
        const text = payload?.text || ''
        if (!text || text === lastUserFinalRef.current) return
        addMessage('user', text, { source: 'voice' })
        lastUserFinalRef.current = text
        if (payload?.duration_seconds) {
          setLatencyMs(Math.round(Number(payload.duration_seconds) * 1000))
        }
        setLiveUserText('')
      }),
      websocket.subscribe('tts_start', () => {
        setLiveAssistantText('')
        setVoiceState('speaking')
        setVoiceStateStore('speaking')
      }),
      websocket.subscribe('assistant_response_chunk', (payload) => {
        const chunk = sanitizeAssistantText(payload?.text_chunk || '')
        if (!chunk || payload?.is_final) return
        setLiveAssistantText((prev) => `${prev}${chunk}`)
      }),
      websocket.subscribe('tts_end', (payload) => {
        if (Number.isFinite(Number(payload?.duration_ms)) && Number(payload.duration_ms) > 0) {
          setLatencyMs(Math.round(Number(payload.duration_ms)))
        }
        finalizeAssistantStreaming()
        setVoiceState('idle')
        setVoiceStateStore('idle')
      }),
      websocket.subscribe('assistant_response', (payload) => {
        const text = sanitizeAssistantText(payload?.text || '')

        if (payload?.latency_ms) {
          setLatencyMs(Math.round(Number(payload.latency_ms)))
        }

        if (!text.trim() || text === lastAssistantFinalRef.current) return
        if (liveAssistantTextRef.current.trim()) return

        addMessage('assistant', text, { source: 'brain', intent: payload?.intent })
        lastAssistantFinalRef.current = text
      }),
      websocket.subscribe('audio_level', (payload) => {
        const levels = Array.isArray(payload?.levels) ? payload.levels : []
        setAudioLevels(levels)
      }),
      websocket.subscribe('tts_completed', (payload) => {
        if (payload?.duration_ms) {
          setLatencyMs(Math.round(Number(payload.duration_ms)))
        }
      }),
      websocket.subscribe('error', (payload) => {
        setVoiceState('error')
        setVoiceStateStore('error')
        addToast({
          type: 'warning',
          title: payload?.code || 'Voice error',
          message: payload?.message || 'Pipeline issue detected',
        })
      }),
    ]

    return () => {
      unsubscribers.forEach((unsubscribe) => unsubscribe?.())
    }
  }, [addMessage, addToast, setVoiceStateStore, websocket])

  // Connection hint logic
  useEffect(() => {
    if (connectionState === 'connecting') {
      if (!connectSinceRef.current) {
        connectSinceRef.current = Date.now()
      }

      const timer = setTimeout(() => {
        if (connectionState === 'connecting') {
          setConnectionHint(`Trying to reach backend on ${BACKEND_WS_URL}...`)
          websocket.reconnect()
        }
      }, 6000)

      return () => clearTimeout(timer)
    }

    connectSinceRef.current = 0
    if (connectionState === 'connected') {
      setConnectionHint('')
    }

    if (connectionState === 'disconnected') {
      setConnectionHint('Backend is offline. Start backend to enable voice.')
    }
  }, [connectionState, websocket])

  // Auto-scroll chat
  useEffect(() => {
    if (!scrollRef.current) return
    scrollRef.current.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, liveAssistantText, liveUserText])

  // Health probe
  useEffect(() => {
    let active = true

    const pollHealth = async () => {
      const abort = new AbortController()
      const timeoutId = setTimeout(() => abort.abort(), 3500)

      try {
        const response = await fetch(BACKEND_HEALTH_URL, {
          method: 'GET',
          cache: 'no-store',
          signal: abort.signal,
        })

        if (!response.ok) {
          if (active) {
            setHealthProbe({
              checked: true,
              reachable: false,
              healthy: false,
              message: `Health endpoint returned ${response.status}`,
            })
          }
          return
        }

        const payload = await response.json().catch(() => ({}))
        if (!active) return

        const healthy = !!payload?.ok
        setHealthProbe({
          checked: true,
          reachable: true,
          healthy,
          message: healthy ? '' : `Backend health status: ${payload?.status || 'degraded'}`,
        })
      } catch {
        if (active) {
          setHealthProbe({
            checked: true,
            reachable: false,
            healthy: false,
            message: 'Health endpoint unreachable',
          })
        }
      } finally {
        clearTimeout(timeoutId)
      }
    }

    pollHealth()
    const timer = setInterval(pollHealth, 10000)

    return () => {
      active = false
      clearInterval(timer)
    }
  }, [])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      manualSessionActiveRef.current = false
      setLiveUserText('')
      setLiveAssistantText('')
      setDisplayedAssistantText('')
      setAudioLevels([])
      setIsTapBusy(false)
      stopLocalSpeechPreview()
    }
  }, [])

  // Tray hooks
  useEffect(() => {
    const removeListening = window.jarvis?.tray?.onListeningToggle?.(() => {
      // Tray listening toggle is currently a renderer-side control.
    })

    const removeMute = window.jarvis?.tray?.onMuteToggle?.((muted) => {
      setMuted(muted)
    })

    return () => {
      removeListening?.()
      removeMute?.()
    }
  }, [setMuted])

  const hasMessages = messages.length > 0 || !!liveUserText || !!liveAssistantText || !!displayedAssistantText

  return (
    <div className='voice-home'>
      {/* ── Top Section: Arc + Waveform + Status ── */}
      <section className='voice-home-top'>
        <div className='voice-hero-copy'>
          <h1>Jarvis Voice Core</h1>
          <p>Low-latency local voice assistant with live conversational streaming</p>
        </div>
        <div style={{ width: '100%', height: '250px', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          <Canvas camera={{ position: [0, 0, 5] }}>
            <ambientLight intensity={0.5} />
            <directionalLight position={[10, 10, 5]} intensity={1} />
            <GeminiBlob state={voiceState.toUpperCase()} audioLevel={Math.max(...audioLevels, 0)} />
          </Canvas>
        </div>
        <div className='voice-status-strip'>
          <span className={`voice-status-pill ${connectionMeta.className}`}>
            <Activity size={14} /> {connectionMeta.text}
          </span>
          <span className={`voice-status-pill ${micMeta.className}`}>
            <Mic size={14} /> {micMeta.text}
          </span>
          {latencyMs ? <span className='voice-status-pill'><Sparkles size={14} /> ~{latencyMs}ms</span> : null}
        </div>
        {healthProbe.checked && (!healthProbe.reachable || !healthProbe.healthy) ? (
          <p className='voice-health-banner'>
            {healthProbe.message || 'Backend health degraded'}
          </p>
        ) : null}
        {connectionHint ? <p className='voice-connection-hint'>{connectionHint}</p> : null}

        {/* Live transcript overlay */}
        {/* Removed floating overlay and integrated into the split bar */}
      </section>

      {/* ── Chat / Conversation Area ── */}
      <section className='voice-home-chat' ref={scrollRef}>
        {!hasMessages ? (
          <div className='voice-home-empty'>
            <h2 className='voice-home-greeting'>Hello, how can I help?</h2>
            <p className='voice-home-subtitle'>
              Tap the mic, type a command, or try a suggestion below
            </p>
            <div className='voice-chip-row'>
              {QUICK_SUGGESTIONS.map((chip) => (
                <button
                  key={chip}
                  type='button'
                  className='voice-chip'
                  onClick={() => sendTextCommand(chip)}
                >
                  {chip}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((message) => (
          <article
            key={message.id}
            className={`voice-bubble ${message.role === 'user' ? 'voice-bubble-user' : 'voice-bubble-jarvis'}`}
          >
            <p>{message.content || ''}</p>
            <small>{new Date(message.timestamp).toLocaleTimeString()}</small>
          </article>
        ))}

        {/* Streaming assistant response */}
        {liveAssistantText ? (
          <div className='voice-streaming-response'>
            <p>
              {displayedAssistantText || liveAssistantText}
              <span className='voice-cursor'>▍</span>
            </p>
          </div>
        ) : null}

        {/* Thinking indicator */}
        {voiceState === 'thinking' && !liveAssistantText ? (
          <div className='voice-streaming-response'>
            <p>
              <span className='voice-streaming-dots'>
                <span />
                <span />
                <span />
              </span>
            </p>
          </div>
        ) : null}
      </section>

      {/* ── Bottom Bar: Split Input/Output ── */}
      <footer className='voice-home-bar'>
        {/* Left Side: User Input Area */}
        <div className={`voice-bar-section voice-bar-user ${voiceState === 'listening' || voiceState === 'transcribing' ? 'active' : ''}`}>
          <button
            type='button'
            className={`voice-home-mic-btn ${isBusy ? 'active' : ''}`}
            onClick={handleMicClick}
            disabled={isTapBusy && !isBusy}
            title={isBusy ? 'Stop / Interrupt' : 'Tap to speak'}
          >
            {isBusy ? <MicOff size={18} /> : <Mic size={18} />}
          </button>

          <div className='voice-streaming-text user'>
            {liveUserText || (typedText ? typedText : 'Ask Jarvis anything...')}
            {liveUserText && <span className='voice-cursor'>▍</span>}
          </div>

          <form
            className='voice-home-input-wrap'
            onSubmit={(event) => {
              event.preventDefault()
              sendTextCommand(typedText)
              setTypedText('')
            }}
          >
            <input
              ref={inputRef}
              className='voice-home-input'
              value={typedText}
              onChange={(event) => setTypedText(event.target.value)}
              placeholder='...'
              aria-label='Type command'
            />
            <button
              type='submit'
              className='voice-home-send-btn'
              disabled={!typedText.trim()}
              title='Send'
            >
              <SendHorizonal size={16} />
            </button>
          </form>
        </div>

        {/* Right Side: Assistant Output Area */}
        <div className={`voice-bar-section voice-bar-assistant ${voiceState === 'speaking' ? 'active' : ''}`}>
          <div className='voice-streaming-text assistant'>
            {voiceState === 'thinking' && !liveAssistantText ? (
              <span className='voice-streaming-dots'>
                <span />
                <span />
                <span />
              </span>
            ) : (
              <>
                {displayedAssistantText || liveAssistantText}
                {(liveAssistantText && displayedAssistantText !== liveAssistantText) && <span className='voice-cursor'>▍</span>}
              </>
            )}
          </div>

          <div className={`voice-home-mini-wave ${canShowWaveform ? 'active' : ''}`} aria-hidden='true'>
            {Array.from({ length: 5 }).map((_, index) => {
              const base = Number(audioLevels[index] || audioLevels[index % Math.max(1, audioLevels.length)] || 0.2)
              const px = Math.max(4, Math.min(18, Math.round(base * 18)))
              return <span key={index} style={{ height: `${px}px` }} />
            })}
          </div>

          <button
            type='button'
            className={`voice-always-on-toggle ${alwaysOnSpeaker ? 'active' : ''}`}
            onClick={() => {
              const next = !alwaysOnSpeaker
              setAlwaysOnSpeaker(next)
              websocket.sendMessage({
                type: 'set_always_on',
                payload: { enabled: next },
              })
              addToast({
                type: 'info',
                title: next ? 'Always-on enabled' : 'Always-on disabled',
                message: next
                  ? 'Jarvis will auto-listen after each response'
                  : 'Manual tap-to-speak mode restored',
              })
            }}
            title={alwaysOnSpeaker ? 'Disable always-on listening' : 'Enable always-on listening'}
          >
            <span className='voice-always-on-dot' />
            <span className='voice-always-on-label'>ON</span>
          </button>

          <button type='button' className='voice-home-settings-btn' onClick={() => navigate('/settings')} title='Settings'>
            <Settings2 size={17} />
          </button>
        </div>
      </footer>
    </div>
  )
}
