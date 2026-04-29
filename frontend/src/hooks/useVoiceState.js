import { useEffect } from 'react'
import { useAppStore } from '../store/appStore'
import { sanitizeAssistantText } from '../utils/textSanitizer'

export function useVoiceState(websocket) {
  const setVoiceState = useAppStore((state) => state.setVoiceState)
  const setCurrentTranscription = useAppStore((state) => state.setCurrentTranscription)
  const appendCurrentTranscription = useAppStore((state) => state.appendCurrentTranscription)
  const clearCurrentTranscription = useAppStore((state) => state.clearCurrentTranscription)
  const appendCurrentResponse = useAppStore((state) => state.appendCurrentResponse)
  const clearCurrentResponse = useAppStore((state) => state.clearCurrentResponse)
  const setCurrentResponse = useAppStore((state) => state.setCurrentResponse)
  const setHealthStatus = useAppStore((state) => state.setHealthStatus)
  const setAuthStatus = useAppStore((state) => state.setAuthStatus)
  const addToast = useAppStore((state) => state.addToast)

  const getChunk = (payload) => payload?.chunk || payload?.text_chunk || payload?.word || payload?.text || ''

  const alwaysOnSpeaker = useAppStore((state) => state.alwaysOnSpeaker)
  const voiceState = useAppStore((state) => state.voiceState)
  const connectionState = useAppStore((state) => state.connectionState)

  // Global auto-restart logic for Always-on Mic
  useEffect(() => {
    if (alwaysOnSpeaker && voiceState === 'idle' && connectionState === 'connected') {
      const timer = setTimeout(() => {
        websocket?.sendMessage({ type: 'start_listening', payload: { source: 'always_on' } })
      }, 1000)
      return () => clearTimeout(timer)
    }
  }, [alwaysOnSpeaker, voiceState, connectionState, websocket])

  useEffect(() => {
    if (!websocket) return

    const unsubscribers = [
      websocket.subscribe('voice_state_change', (payload) => {
        if (payload?.state) {
          setVoiceState(payload.state)
          window.jarvis?.tray?.setState?.(payload.state)
        }
      }),
      websocket.subscribe('transcription_result', (payload) => {
        const text = payload?.text || ''
        clearCurrentTranscription()
        setCurrentTranscription(text)
      }),
      websocket.subscribe('transcript_chunk', (payload) => {
        const chunk = getChunk(payload)
        if (!chunk) return
        if (payload?.is_final && payload?.text) {
          clearCurrentTranscription()
          setCurrentTranscription(payload.text)
          return
        }

        if (payload?.text) {
          clearCurrentTranscription()
          setCurrentTranscription(payload.text)
        } else {
          appendCurrentTranscription(chunk)
        }
      }),
      websocket.subscribe('assistant_response_chunk', (payload) => {
        const chunk = sanitizeAssistantText(getChunk(payload))
        if (!chunk) return
        appendCurrentResponse(chunk)
      }),
      websocket.subscribe('assistant_response', (payload) => {
        const text = sanitizeAssistantText(payload?.text || useAppStore.getState().currentResponse)
        if (text.trim()) {
          setCurrentResponse(text)
          window.jarvis?.tray?.setLastResponse?.(text)
        }

        if (payload?.action_taken) {
          const success = !!payload.action_taken.success
          addToast({
            type: success ? 'success' : 'warning',
            title: success ? 'Action completed' : 'Action failed',
            message: payload.action_taken.message || (success ? 'Done' : 'Unable to complete action'),
          })
        }

        clearCurrentResponse()
      }),
      websocket.subscribe('tts_start', () => {
        setVoiceState('speaking')
      }),
      websocket.subscribe('tts_end', () => {
        setVoiceState('idle')
      }),
      // Legacy aliases for backward compatibility with older backend builds.
      websocket.subscribe('tts_started', () => {
        setVoiceState('speaking')
      }),
      websocket.subscribe('tts_completed', () => {
        setVoiceState('idle')
      }),
      websocket.subscribe('health_status', (payload) => {
        const apis = payload?.apis || {}
        setHealthStatus({
          microphone: !!payload?.microphone,
          modelLoaded: !!(payload?.model_loaded ?? payload?.modelLoaded),
          apis: {
            claude: !!apis.claude,
            gemini: !!apis.gemini,
            groq: !!apis.groq,
            openrouter: !!apis.openrouter,
            ollama: !!apis.ollama,
            elevenlabs: !!apis.elevenlabs,
          },
          details: payload?.details || {},
          websocket: !!payload?.websocket,
        })
      }),
      websocket.subscribe('auth_result', (payload) => {
        setAuthStatus({
          verified: !!payload?.verified,
          confidence: Number(payload?.confidence || 0),
          mode: payload?.mode || 'voice',
          pinRequired: !!payload?.pin_required,
        })

        if (payload?.pin_required) {
          addToast({
            type: 'warning',
            title: 'PIN fallback available',
            message: 'Voice verification failed repeatedly. You can verify with PIN in settings.',
          })
        }
      }),
      websocket.subscribe('auth_challenge', (payload) => {
        if (!payload?.phrase) return
        addToast({
          type: 'info',
          title: 'Voice challenge',
          message: `Please repeat: ${payload.phrase}`,
        })
      }),
      websocket.subscribe('auth_challenge_result', (payload) => {
        addToast({
          type: payload?.passed ? 'success' : 'warning',
          title: payload?.passed ? 'Challenge passed' : 'Challenge failed',
          message: payload?.passed ? 'Identity verified.' : 'Could not verify challenge response.',
        })
      }),
      websocket.subscribe('error', (payload) => {
        addToast({
          type: 'warning',
          title: payload?.code || 'Backend error',
          message: payload?.message || 'Something went wrong',
        })
      }),
      websocket.subscribe('pong', () => {
        // Heartbeat acknowledgement; no UI update needed.
      }),
    ]

    return () => {
      unsubscribers.forEach((unsubscribe) => unsubscribe?.())
    }
  }, [
    websocket,
    addToast,
    appendCurrentResponse,
    appendCurrentTranscription,
    clearCurrentResponse,
    clearCurrentTranscription,
    setCurrentResponse,
    setCurrentTranscription,
    setAuthStatus,
    setHealthStatus,
    setVoiceState,
  ])
}
