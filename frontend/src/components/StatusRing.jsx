import { STATE_VISUALS } from '../utils/constants'

export default function StatusRing({ voiceState, connectionState }) {
  const visual = STATE_VISUALS[voiceState] || STATE_VISUALS.idle

  return (
    <div className='status-ring-wrap'>
      <div className='status-ring' style={{ borderColor: visual.color, boxShadow: `0 0 22px ${visual.color}` }} />
      <div className='status-labels'>
        <span>{voiceState}</span>
        <span className={connectionState === 'connected' ? 'ok' : 'warn'}>{connectionState}</span>
      </div>
    </div>
  )
}
