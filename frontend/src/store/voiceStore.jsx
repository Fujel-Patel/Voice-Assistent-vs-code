/**
 * Frontend State Store — Voice State
 * =====================================
 * Simple React context + useReducer store for Jarvis voice state.
 * Used by useVoiceState.js hook and UI components.
 *
 * This is a lightweight alternative to Zustand for keeping
 * the frontend dependency count low.
 *
 * State shape:
 *   voiceState: 'idle' | 'wake_detected' | 'listening' | 'transcribing' | 'thinking' | 'speaking'
 *   transcript:  latest transcribed text
 *   response:    latest AI response (may be streaming)
 *   latencyMs:   last round-trip latency
 *   isStreaming: whether Claude is currently streaming
 *   error:       last error message (or null)
 */

import { createContext, useContext, useReducer } from 'react'

// ── Initial state ──────────────────────────────────────

const initialState = {
  voiceState: 'idle',
  transcript: '',
  response: '',
  latencyMs: null,
  isStreaming: false,
  error: null,
}

// ── Action types ───────────────────────────────────────

export const VoiceActions = {
  SET_VOICE_STATE:   'SET_VOICE_STATE',
  SET_TRANSCRIPT:    'SET_TRANSCRIPT',
  APPEND_RESPONSE:   'APPEND_RESPONSE',
  SET_RESPONSE_DONE: 'SET_RESPONSE_DONE',
  SET_LATENCY:       'SET_LATENCY',
  SET_ERROR:         'SET_ERROR',
  CLEAR_ERROR:       'CLEAR_ERROR',
  RESET:             'RESET',
}

// ── Reducer ────────────────────────────────────────────

function voiceReducer(state, action) {
  switch (action.type) {
    case VoiceActions.SET_VOICE_STATE:
      return { ...state, voiceState: action.payload, error: null }

    case VoiceActions.SET_TRANSCRIPT:
      return { ...state, transcript: action.payload }

    case VoiceActions.APPEND_RESPONSE:
      return {
        ...state,
        response: state.response + action.payload,
        isStreaming: true,
      }

    case VoiceActions.SET_RESPONSE_DONE:
      return {
        ...state,
        response: action.payload ?? state.response,
        isStreaming: false,
      }

    case VoiceActions.SET_LATENCY:
      return { ...state, latencyMs: action.payload }

    case VoiceActions.SET_ERROR:
      return { ...state, error: action.payload, voiceState: 'idle' }

    case VoiceActions.CLEAR_ERROR:
      return { ...state, error: null }

    case VoiceActions.RESET:
      return { ...initialState }

    default:
      return state
  }
}

// ── Context ────────────────────────────────────────────

const VoiceStateContext = createContext(null)
const VoiceDispatchContext = createContext(null)

export function VoiceStateProvider({ children }) {
  const [state, dispatch] = useReducer(voiceReducer, initialState)
  return (
    <VoiceStateContext.Provider value={state}>
      <VoiceDispatchContext.Provider value={dispatch}>
        {children}
      </VoiceDispatchContext.Provider>
    </VoiceStateContext.Provider>
  )
}

// ── Hooks ──────────────────────────────────────────────

export function useVoiceStore() {
  const ctx = useContext(VoiceStateContext)
  if (!ctx) throw new Error('useVoiceStore must be inside VoiceStateProvider')
  return ctx
}

export function useVoiceDispatch() {
  const ctx = useContext(VoiceDispatchContext)
  if (!ctx) throw new Error('useVoiceDispatch must be inside VoiceStateProvider')
  return ctx
}
