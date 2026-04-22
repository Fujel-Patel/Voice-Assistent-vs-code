import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAppStore } from '../store/appStore'

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
      setLatencyMetrics({
        captureMs: Number(payload?.capture_latency_ms || latencyMetrics.captureMs || 0),
        backendMs: Number(payload?.processing_latency_ms || 0),
        roundtripMs: requestRoundtrip,
        totalMs: Number(payload?.total_pipeline_latency_ms || 0),
      })
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

  useEffect(() => {
    return () => {
      if (finalizedRef.current) return
      void cleanupRecording()
    }
  }, [])

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
    <div className='settings-page'>
      <header className='settings-page-header'>
        <div>
          <h2>Voice Enrollment</h2>
          <p>Record three clear samples to build your voice profile.</p>
        </div>
        <button className='settings-return-btn' onClick={() => navigate('/')}>
          Abort Enrollment
        </button>
      </header>

      <div className='settings-content'>
        <section className='settings-section'>
          <header className='settings-section-header'>
            <h3>Step {currentStep} of {totalSteps}</h3>
            <p>Speak clearly when recording starts.</p>
          </header>

          <div className='settings-api-banner'>
            <strong>Say this phrase:</strong>
            <p className='enrollment-phrase-progress'>
              {phraseWords.map((word, index) => {
                let className = 'phrase-word'
                if (index < matchedWordCount) {
                  className += ' matched'
                } else if (index === matchedWordCount && recording) {
                  className += ' active'
                }
                return (
                  <span className={className} key={`${word}-${index}`}>
                    {word}
                  </span>
                )
              })}
            </p>
            <small className='enrollment-progress-meta'>
              Progress: {matchedWordCount}/{phraseWords.length} words matched
            </small>
            {recording ? (
              <small className='enrollment-progress-live'>Live: {liveTranscript || 'listening...'}</small>
            ) : null}
          </div>

          <div className='about-grid'>
            <div>
              <span>Samples Captured</span>
              <strong>{samplesCaptured} / {totalSteps}</strong>
            </div>
            <div>
              <span>Profile Strength</span>
              <strong>{profileStrength}%</strong>
            </div>
            <div>
              <span>Database</span>
              <strong>{dbConnected ? 'Connected' : 'Disconnected'}</strong>
            </div>
            <div>
              <span>Speech Realtime</span>
              <strong>{speechRecognitionSupported ? 'Enabled' : 'Not supported in this browser'}</strong>
            </div>
          </div>

          <div className='about-grid'>
            <div>
              <span>Capture Latency</span>
              <strong>{latencyMetrics.captureMs} ms</strong>
            </div>
            <div>
              <span>Backend Latency</span>
              <strong>{latencyMetrics.backendMs} ms</strong>
            </div>
            <div>
              <span>Roundtrip Latency</span>
              <strong>{latencyMetrics.roundtripMs} ms</strong>
            </div>
            <div>
              <span>Total Pipeline</span>
              <strong>{latencyMetrics.totalMs} ms</strong>
            </div>
          </div>

          <div className='about-actions'>
            {!recording ? (
              <button onClick={startRecording} disabled={submitting}>
                Start Recording
              </button>
            ) : (
              <button onClick={stopRecording} disabled={submitting}>
                Stop Recording
              </button>
            )}

            <button onClick={() => navigate('/settings')} disabled={recording || submitting}>
              Back to Settings
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}
