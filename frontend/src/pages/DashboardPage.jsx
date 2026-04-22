import { useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAppStore } from '../store/appStore'

/**
 * DashboardPage.jsx — Debug dashboard page (route: /dashboard)
 *
 * Full-screen SYNTHETIC_INTEL dashboard with the terminal console,
 * system stats, hero panel, and side navigation.
 *
 * Wraps the DebugConsole component which contains the complete layout.
 */

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
    <div className='dashboard-page'>
      <header className='dashboard-header'>
        <div>
          <h2>System Dashboard</h2>
          <p>Live overview of connection, voice pipeline, auth, and transcript streams.</p>
        </div>
        <div className='dashboard-actions'>
          <button className='settings-return-btn' onClick={() => navigate('/')}>
            HUD View
          </button>
          <button className='settings-return-btn' onClick={() => navigate('/settings')}>
            Open Settings
          </button>
        </div>
      </header>

      <section className='dashboard-grid'>
        <article className='dashboard-card'>
          <h3>Connection</h3>
          <div className='dashboard-stat-row'>
            <span>WebSocket</span>
            <strong>{String(connectionState || 'disconnected').toUpperCase()}</strong>
          </div>
          <div className='dashboard-stat-row'>
            <span>Voice State</span>
            <strong>{String(voiceState || 'idle').toUpperCase()}</strong>
          </div>
          <div className='dashboard-stat-row'>
            <span>Auth Mode</span>
            <strong>{String(authStatus?.mode || 'unknown').toUpperCase()}</strong>
          </div>
          <div className='dashboard-stat-row'>
            <span>Verified</span>
            <strong>{authStatus?.verified ? 'YES' : 'NO'}</strong>
          </div>
        </article>

        <article className='dashboard-card'>
          <h3>Health</h3>
          <div className='dashboard-stat-row'>
            <span>Microphone</span>
            <strong>{healthStatus?.microphone ? 'READY' : 'OFFLINE'}</strong>
          </div>
          <div className='dashboard-stat-row'>
            <span>Model Loaded</span>
            <strong>{healthStatus?.modelLoaded ? 'YES' : 'NO'}</strong>
          </div>
          <div className='dashboard-pill-row'>
            {Object.entries(healthStatus?.apis || {}).map(([api, ok]) => (
              <span key={api} className={`dashboard-pill ${ok ? 'ok' : 'warn'}`}>
                {api}: {ok ? 'ok' : 'down'}
              </span>
            ))}
          </div>
        </article>

        <article className='dashboard-card dashboard-stream-card'>
          <h3>Live Streams</h3>
          <div className='dashboard-stream-block'>
            <label>Transcript Stream</label>
            <p>{currentTranscription || 'Waiting for transcript chunks...'}</p>
          </div>
          <div className='dashboard-stream-block'>
            <label>Response Stream</label>
            <p>{currentResponse || 'Waiting for response chunks...'}</p>
          </div>
        </article>
      </section>

      <section className='dashboard-log-card'>
        <div className='dashboard-log-header'>
          <h3>Recent Conversation Events</h3>
          <span>{recentMessages.length} entries</span>
        </div>
        <div className='dashboard-log-list'>
          {recentMessages.length === 0 ? (
            <p className='dashboard-empty'>No messages yet. Start by speaking or typing in HUD.</p>
          ) : (
            recentMessages.map((message) => (
              <article key={message.id} className='dashboard-log-item'>
                <header>
                  <strong>{message.role === 'assistant' ? 'Jarvis' : 'User'}</strong>
                  <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
                </header>
                <p>{message.content}</p>
                {message.intent ? <small>intent: {message.intent}</small> : null}
              </article>
            ))
          )}
        </div>
      </section>
    </div>
  )
}
