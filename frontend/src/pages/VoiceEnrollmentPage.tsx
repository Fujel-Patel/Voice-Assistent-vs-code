import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, Mic, Square, User, CheckCircle, Database, Zap, Clock, Loader2 } from 'lucide-react'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAppStore } from '../store/appStore'
import { cn } from '../lib/utils'

function tokenizePhrase(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9\s]/gi, ' ')
    .split(/\s+/)
    .filter(Boolean)
}

function countLeadingMatch(targetWords, spokenWords) {
  const limit = Math.min(targetWords.length, spokenWords.length)
  let index = 0
  while (index < limit && targetWords[index] === spokenWords[index]) {
    index += 1
  }
  return index
}

function isEnrollmentCompleted(payload) {
  if (!payload || payload.success !== true) {
    return false
  }

  if (payload.complete === true) {
    return true
  }

  const message = String(payload.message || '').toLowerCase()
  return message.includes('voice profile created') || message.includes('enrollment complete')
}

export default function VoiceEnrollmentPage() {
  const navigate = useNavigate()
  const websocket = useWebSocket()
  const addToast = useAppStore((state) => state.addToast)

  const [currentStep, setCurrentStep] = useState(1)
  const [totalSteps, setTotalSteps] = useState(3)
  const [phrase, setPhrase] = useState('Preparing enrollment...')
  const [recording, setRecording] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [profileStrength, setProfileStrength] = useState(0)
  const [samplesCaptured, setSamplesCaptured] = useState(0)
  const [liveTranscript, setLiveTranscript] = useState('')
  const [dbConnected, setDbConnected] = useState(true)
  const [latencyMetrics, setLatencyMetrics] = useState({
    captureMs: 0,
    backendMs: 0,
    roundtripMs: 0,
    totalMs: 0,
  })

  const streamRef = useRef(null)
  const contextRef = useRef(null)
  const sourceRef = useRef(null)
  const processorRef = useRef(null)
  const recognitionRef = useRef(null)
  const chunksRef = useRef([])
  const sampleRateRef = useRef(16000)
  const finalizedRef = useRef(false)
  const recordingStartMsRef = useRef(0)
  const submitSentMsRef = useRef(0)

  const phraseWords = useMemo(() => tokenizePhrase(phrase), [phrase])
  const spokenWords = useMemo(() => tokenizePhrase(liveTranscript), [liveTranscript])
  const matchedWordCount = useMemo(() => countLeadingMatch(phraseWords, spokenWords), [phraseWords, spokenWords])

  const speechRecognitionSupported = typeof window !== 'undefined' &&
    (window.SpeechRecognition || window.webkitSpeechRecognition)

  const sendStartEnrollment = useCallback(() => {
    websocket.sendMessage({
      type: 'start_voice_enrollment',
      payload: { user_id: 'default_user' },
    })
  }, [websocket])

  useEffect(() => {
    const unsub = websocket.subscribe('enrollment_status', (payload) => {
      if (payload?.error) {
        setSubmitting(false)
        if (typeof payload?.db_connected === 'boolean') {
          setDbConnected(payload.db_connected)
        }
        addToast({ type: 'warning', title: 'Enrollment issue', message: payload.error })
        return
      }

      if (typeof payload?.db_connected === 'boolean') {
        setDbConnected(payload.db_connected)
      }

      const requestRoundtrip = submitSentMsRef.current ? Math.max(0, Date.now() - submitSentMsRef.current) : 0
      setLatencyMetrics((prev) => ({
        captureMs: Number(payload?.capture_latency_ms || prev.captureMs || 0),
        backendMs: Number(payload?.processing_latency_ms || 0),
        roundtripMs: requestRoundtrip,
        totalMs: Number(payload?.total_pipeline_latency_ms || 0),
      }))
      submitSentMsRef.current = 0

      if (isEnrollmentCompleted(payload)) {
        setSubmitting(false)
        setProfileStrength(Number(payload.profile_strength || 0))
        addToast({ type: 'success', title: 'Enrollment complete', message: payload.message || 'Voice profile saved.' })
        finalizedRef.current = true
        navigate('/settings')
        return
      }

      if (typeof payload?.step === 'number') {
        setCurrentStep(payload.step)
        setSamplesCaptured(Math.max(0, payload.step - 1))
      }
      if (typeof payload?.total_steps === 'number') {
        setTotalSteps(payload.total_steps)
      }
      if (typeof payload?.profile_strength === 'number') {
        setProfileStrength(payload.profile_strength)
      }

      const nextPhrase = payload?.next_phrase || payload?.phrase
      if (nextPhrase) {
        setPhrase(nextPhrase)
        setLiveTranscript('')
      }

      if (payload?.complete) {
        websocket.sendMessage({
          type: 'complete_voice_enrollment',
          payload: { user_id: 'default_user' },
        })
      }

      setSubmitting(false)
    })

    const timer = setTimeout(sendStartEnrollment, 250)
    return () => {
      clearTimeout(timer)
      unsub?.()
    }
  }, [addToast, navigate, sendStartEnrollment, websocket])

  const cleanupRecording = useCallback(async () => {
    try {
      if (recognitionRef.current) {
        recognitionRef.current.stop()
      }
      processorRef.current?.disconnect()
      sourceRef.current?.disconnect()
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop())
      }
      if (contextRef.current && contextRef.current.state !== 'closed') {
        await contextRef.current.close()
      }
    } catch {
      // Keep cleanup best-effort.
    }

    processorRef.current = null
    sourceRef.current = null
    streamRef.current = null
    contextRef.current = null
    recognitionRef.current = null
  }, [])

  useEffect(() => {
    return () => {
      if (finalizedRef.current) return
      void cleanupRecording()
    }
  }, [cleanupRecording])

  const startSpeechRecognition = useCallback(() => {
    const SpeechRecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognitionCtor) {
      return
    }

    const recognition = new SpeechRecognitionCtor()
    recognition.lang = 'en-US'
    recognition.continuous = true
    recognition.interimResults = true
    recognition.maxAlternatives = 1

    recognition.onresult = (event) => {
      let transcript = ''
      for (let index = 0; index < event.results.length; index += 1) {
        const value = event.results[index]?.[0]?.transcript
        if (value) {
          transcript += `${value} `
        }
      }
      setLiveTranscript(transcript.trim())
    }

    recognition.onerror = () => {
      // Ignore transient recognition errors; audio sample still records and submits.
    }

    recognitionRef.current = recognition
    recognition.start()
  }, [])

  const startRecording = useCallback(async () => {
    if (recording || submitting) return

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })

      const AudioContextCtor = window.AudioContext || window.webkitAudioContext
      const audioContext = new AudioContextCtor()
      const source = audioContext.createMediaStreamSource(stream)
      const processor = audioContext.createScriptProcessor(4096, 1, 1)

      chunksRef.current = []
      sampleRateRef.current = audioContext.sampleRate
      processor.onaudioprocess = (event) => {
        const input = event.inputBuffer.getChannelData(0)
        chunksRef.current.push(new Float32Array(input))
      }

      source.connect(processor)
      processor.connect(audioContext.destination)

      streamRef.current = stream
      contextRef.current = audioContext
      sourceRef.current = source
      processorRef.current = processor
      recordingStartMsRef.current = Date.now()
      setLiveTranscript('')
      setRecording(true)
      startSpeechRecognition()
    } catch (error) {
      addToast({
        type: 'warning',
        title: 'Microphone unavailable',
        message: String(error),
      })
    }
  }, [addToast, recording, startSpeechRecognition, submitting])

  const stopRecording = useCallback(async () => {
    if (!recording || submitting) return
    setRecording(false)
    setSubmitting(true)

    const captureDurationMs = recordingStartMsRef.current ? Math.max(0, Date.now() - recordingStartMsRef.current) : 0
    setLatencyMetrics((prev) => ({
      ...prev,
      captureMs: captureDurationMs,
    }))

    const recorded = chunksRef.current
    chunksRef.current = []

    await cleanupRecording()

    if (!recorded.length) {
      setSubmitting(false)
      addToast({ type: 'warning', title: 'No audio captured', message: 'Please try recording again.' })
      return
    }

    const total = recorded.reduce((count, chunk) => count + chunk.length, 0)
    const merged = new Float32Array(total)
    let offset = 0
    for (const chunk of recorded) {
      merged.set(chunk, offset)
      offset += chunk.length
    }

    const pcm16 = new Int16Array(merged.length)
    for (let index = 0; index < merged.length; index += 1) {
      const sample = Math.max(-1, Math.min(1, merged[index]))
      pcm16[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff
    }

    const bytes = new Uint8Array(pcm16.buffer)
    let binary = ''
    for (let i = 0; i < bytes.length; i += 1) {
      binary += String.fromCharCode(bytes[i])
    }
    const audioBase64 = btoa(binary)

    websocket.sendMessage({
      type: 'submit_voice_sample',
      payload: {
        user_id: 'default_user',
        step: currentStep,
        audio_base64: audioBase64,
        sample_rate: sampleRateRef.current,
        transcript_text: liveTranscript || undefined,
        capture_duration_ms: captureDurationMs,
      },
    })
    submitSentMsRef.current = Date.now()
  }, [addToast, cleanupRecording, currentStep, liveTranscript, recording, submitting, websocket])

  return (
    <div className="min-h-full p-6">
      <header className="flex items-start justify-between mb-6 gap-4">
        <div>
          <h2 className="text-xl font-semibold text-foreground">Voice Enrollment</h2>
          <p className="mt-1 text-sm text-muted-foreground">Record three clear samples to build your voice profile.</p>
        </div>
        <button
          className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-white/5 text-muted-foreground hover:text-foreground hover:bg-white/10 border border-white/10 transition-all"
          onClick={() => navigate('/')}
        >
          <ArrowLeft className="w-4 h-4" />
          Abort Enrollment
        </button>
      </header>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="space-y-6 max-w-2xl"
      >
        <div className="p-6 rounded-xl glass">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-10 h-10 rounded-full bg-cyan-400/10 border border-cyan-400/20">
                <span className="text-sm font-mono text-cyan-400">{currentStep}/{totalSteps}</span>
              </div>
              <div>
                <h3 className="text-sm font-medium text-foreground">Step {currentStep} of {totalSteps}</h3>
                <p className="text-xs text-muted-foreground">Speak clearly when recording starts.</p>
              </div>
            </div>
            {profileStrength > 0 && (
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4 text-green-400" />
                <span className="text-sm font-mono text-green-400">{profileStrength}%</span>
              </div>
            )}
          </div>

          <div className="p-4 rounded-lg bg-white/5 border border-white/10 mb-4">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
              <strong className="text-sm text-foreground">Say this phrase:</strong>
            </div>
            <p className="text-lg font-medium text-foreground mb-2 leading-relaxed">
              {phraseWords.map((word, index) => (
                <span
                  key={`${word}-${index}`}
                  className={cn(
                    "px-1 mx-0.5 rounded transition-all duration-200",
                    index < matchedWordCount && "bg-green-400/20 text-green-400",
                    index === matchedWordCount && recording && "bg-cyan-400/20 text-cyan-400 animate-pulse"
                  )}
                >
                  {word}
                </span>
              ))}
            </p>
            {recording && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                {liveTranscript || 'Listening...'}
              </div>
            )}
            <small className="text-xs text-muted-foreground mt-2 block">
              Progress: {matchedWordCount}/{phraseWords.length} words matched
            </small>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-4">
            {[
              { label: 'Samples Captured', value: `${samplesCaptured} / ${totalSteps}`, icon: User },
              { label: 'Profile Strength', value: `${profileStrength}%`, icon: CheckCircle },
              { label: 'Database', value: dbConnected ? 'Connected' : 'Disconnected', icon: Database, ok: dbConnected },
              { label: 'Speech Realtime', value: speechRecognitionSupported ? 'Enabled' : 'Not supported', icon: Zap, ok: speechRecognitionSupported },
            ].map(({ label, value, icon: Icon, ok }) => (
              <div key={label} className="flex items-center gap-3 p-3 rounded-lg bg-white/5">
                <Icon className={cn(
                  "w-4 h-4",
                  ok === true ? "text-green-400" : ok === false ? "text-amber-400" : "text-muted-foreground"
                )} />
                <div>
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className={cn(
                    "text-sm font-mono",
                    ok === true ? "text-green-400" : ok === false ? "text-amber-400" : "text-foreground"
                  )}>{value}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 gap-3 mb-4">
            {[
              { label: 'Capture Latency', value: `${latencyMetrics.captureMs} ms`, icon: Mic },
              { label: 'Backend Latency', value: `${latencyMetrics.backendMs} ms`, icon: Clock },
              { label: 'Roundtrip Latency', value: `${latencyMetrics.roundtripMs} ms`, icon: Zap },
              { label: 'Total Pipeline', value: `${latencyMetrics.totalMs} ms`, icon: Loader2 },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="flex items-center gap-3 p-3 rounded-lg bg-white/5">
                <Icon className="w-4 h-4 text-cyan-400/70" />
                <div>
                  <p className="text-xs text-muted-foreground">{label}</p>
                  <p className="text-sm font-mono text-cyan-400/90">{value}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="flex gap-3">
            {!recording ? (
              <button
                onClick={startRecording}
                disabled={submitting}
                className={cn(
                  "flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-medium transition-all",
                  "bg-cyan-400 text-background hover:bg-cyan-300",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
                )}
              >
                <Mic className="w-4 h-4" />
                Start Recording
              </button>
            ) : (
              <button
                onClick={stopRecording}
                disabled={submitting}
                className={cn(
                  "flex items-center gap-2 px-6 py-3 rounded-lg text-sm font-medium transition-all",
                  "bg-red-400 text-background hover:bg-red-300 animate-pulse",
                  "disabled:opacity-50 disabled:cursor-not-allowed"
                )}
              >
                <Square className="w-4 h-4" />
                Stop Recording
              </button>
            )}

            <button
              onClick={() => navigate('/settings')}
              disabled={recording || submitting}
              className={cn(
                "flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-medium transition-all",
                "bg-white/5 text-muted-foreground hover:text-foreground hover:bg-white/10 border border-white/10",
                "disabled:opacity-50 disabled:cursor-not-allowed"
              )}
            >
              Back to Settings
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  )
}