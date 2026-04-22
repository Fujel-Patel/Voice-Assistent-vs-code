import { useMemo } from 'react'

export default function StatusBar({ voiceState, connectionState, healthStatus, authStatus }) {
  const healthItems = useMemo(
    () => [
      { label: 'Mic', ok: !!healthStatus?.microphone },
      { label: 'Model', ok: !!healthStatus?.modelLoaded },
      { label: 'API', ok: Object.values(healthStatus?.apis || {}).some(Boolean) },
    ],
    [healthStatus],
  )

  return (
    <footer className='status-bar'>
      <div className='status-pills'>
        <span className='pill'>{`Voice: ${voiceState}`}</span>
        <span className='pill'>{`WS: ${connectionState}`}</span>
        <span className={`pill ${authStatus?.verified ? 'ok' : 'warn'}`}>
          {authStatus?.verified ? `Auth: Verified (${Math.round((authStatus?.confidence || 0) * 100)}%)` : 'Auth: Unverified'}
        </span>
      </div>
      <div className='status-pills'>
        {healthItems.map((item) => (
          <span key={item.label} className={`pill ${item.ok ? 'ok' : 'warn'}`}>
            {item.label}
          </span>
        ))}
      </div>
    </footer>
  )
}
