import { useMemo } from 'react'
import ArcReactor from './ArcReactor'
import Waveform from './Waveform'
import StatusRing from './StatusRing'
import ChatHistory from './ChatHistory'
import StatusBar from './StatusBar'
import ToastHost from './Toast'
import { useAppStore } from '../store/appStore'

export default function HUD({ sendMessage, connectionState }) {
  const voiceState = useAppStore((state) => state.voiceState)
  const healthStatus = useAppStore((state) => state.healthStatus)
  const authStatus = useAppStore((state) => state.authStatus)

  const audioLevel = useMemo(() => {
    if (voiceState === 'speaking') return 0.55
    if (voiceState === 'listening') return 0.75
    if (voiceState === 'thinking') return 0.3
    return 0.18
  }, [voiceState])

  return (
    <div className='hud'>
      <header className='hud-title app-drag'>
        <h1>JARVIS</h1>
        <p>Arc Interface</p>
      </header>

      <main className='hud-main'>
        <aside className='hud-left'>
          <StatusRing voiceState={voiceState} connectionState={connectionState} />
          <Waveform audioLevel={audioLevel} isActive={voiceState !== 'idle'} />
        </aside>

        <section className='hud-core'>
          <ArcReactor state={voiceState} audioLevel={audioLevel} />
        </section>

        <aside className='hud-right'>
          <ChatHistory sendMessage={sendMessage} />
        </aside>
      </main>

      <StatusBar
        voiceState={voiceState}
        connectionState={connectionState}
        healthStatus={healthStatus}
        authStatus={authStatus}
      />
      <ToastHost />
    </div>
  )
}
