import { create } from 'zustand'
import { devtools, persist } from 'zustand/middleware'
import { SETTINGS_DEFAULTS } from '../utils/settingsDefaults'

export const useAppStore = create(
  devtools(
    persist(
      (set) => ({
        voiceState: 'idle',
        isConnected: false,
        isMuted: false,
        connectionState: 'disconnected',
        alwaysOnSpeaker: false,
        theme: 'dark',


        messages: [],
        currentTranscription: '',
        currentResponse: '',

        isChatOpen: false,
        isSettingsOpen: false,
        lastRoute: '/',
        activeSettingsSection: 'general',
        toasts: [],

        settings: {
          ...SETTINGS_DEFAULTS,
        },

        healthStatus: {
          microphone: false,
          modelLoaded: false,
          apis: {
            claude: false,
            gemini: false,
            groq: false,
            openrouter: false,
            ollama: false,
            elevenlabs: false,
          },
        },
        browserMicPermission: 'unknown',
        authStatus: {
          verified: false,
          confidence: 0,
          mode: 'unknown',
          pinRequired: false,
        },

        setVoiceState: (voiceState) => set({ voiceState }),
        setConnectionState: (connectionState) =>
          set({
            connectionState,
            isConnected: connectionState === 'connected',
          }),
        setMuted: (isMuted) => set({ isMuted }),
        setAlwaysOnSpeaker: (alwaysOnSpeaker) => set({ alwaysOnSpeaker }),
        toggleTheme: () => set((state) => ({ theme: state.theme === 'dark' ? 'light' : 'dark' })),


        addMessage: (role, content, metadata = {}) =>
          set((state) => ({
            messages: [
              ...state.messages,
              {
                id: `${Date.now()}-${Math.random()}`,
                role,
                content,
                timestamp: new Date().toISOString(),
                intent: metadata.intent || null,
                ...metadata,
              },
            ],
          })),
        setCurrentTranscription: (currentTranscription) => set({ currentTranscription }),
        appendCurrentTranscription: (chunk) =>
          set((state) => ({
            currentTranscription: `${state.currentTranscription || ''}${chunk || ''}`,
          })),
        clearCurrentTranscription: () => set({ currentTranscription: '' }),
        setCurrentResponse: (currentResponse) => set({ currentResponse }),
        appendCurrentResponse: (chunk) =>
          set((state) => ({
            currentResponse: `${state.currentResponse || ''}${chunk || ''}`,
          })),
        clearCurrentResponse: () => set({ currentResponse: '' }),

        toggleChat: () => set((state) => ({ isChatOpen: !state.isChatOpen })),
        setChatOpen: (isChatOpen) => set({ isChatOpen }),
        setLastRoute: (lastRoute) => set({ lastRoute }),
        setActiveSettingsSection: (activeSettingsSection) => set({ activeSettingsSection }),
        addToast: (toast) =>
          set((state) => {
            const id = `${Date.now()}-${Math.random()}`
            const next = [...state.toasts, { id, ...toast }]
            return { toasts: next.slice(-3) }
          }),
        removeToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
        updateSettings: (key, value) =>
          set((state) => ({
            settings: {
              ...state.settings,
              [key]: value,
            },
          })),
        updateManySettings: (settingsPatch) =>
          set((state) => ({
            settings: {
              ...state.settings,
              ...(settingsPatch || {}),
            },
          })),
        resetSettingsToDefaults: () =>
          set({
            settings: {
              ...SETTINGS_DEFAULTS,
            },
          }),
        setHealthStatus: (healthStatus) => set({ healthStatus }),
        setBrowserMicPermission: (browserMicPermission) => set({ browserMicPermission }),
        setAuthStatus: (authStatus) =>
          set((state) => ({
            authStatus: {
              ...state.authStatus,
              ...(authStatus || {}),
            },
          })),
      }),
      {
        name: 'jarvis-app-store',
        partialize: (state) => ({
          settings: state.settings,
          isMuted: state.isMuted,
          alwaysOnSpeaker: state.alwaysOnSpeaker,
          lastRoute: state.lastRoute,
          activeSettingsSection: state.activeSettingsSection,
          messages: state.messages,
        }),
      },
    ),
    { name: 'jarvis-app-store' },
  ),
)
