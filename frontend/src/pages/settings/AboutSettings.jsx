import SettingsSection from '../../components/settings/SettingsSection'

export default function AboutSettings({ systemInfo, onCheckUpdates, onResetAll, usage }) {
  return (
    <>
      <SettingsSection title='About Jarvis' description='Version, runtime details, and resource usage.'>
        <div className='about-header'>
          <div className='about-reactor' />
          <div>
            <h4>JARVIS Voice Assistant</h4>
            <p>Version 1.0.0</p>
          </div>
        </div>

        <div className='about-grid'>
          <div>
            <span>Electron</span>
            <strong>{systemInfo?.electron || 'Unknown'}</strong>
          </div>
          <div>
            <span>Node.js</span>
            <strong>{systemInfo?.node || 'Unknown'}</strong>
          </div>
          <div>
            <span>Python</span>
            <strong>{systemInfo?.python || 'Unknown'}</strong>
          </div>
          <div>
            <span>OS</span>
            <strong>{systemInfo?.platform || 'Unknown'}</strong>
          </div>
        </div>

        <div className='about-grid'>
          <div>
            <span>Whisper</span>
            <strong>{systemInfo?.whisper_model || 'small'}</strong>
          </div>
          <div>
            <span>TTS</span>
            <strong>{systemInfo?.tts_engine || 'ElevenLabs'}</strong>
          </div>
          <div>
            <span>Claude Today</span>
            <strong>{usage?.claude_today || '0 tokens'}</strong>
          </div>
          <div>
            <span>Cost Estimate</span>
            <strong>{usage?.cost_today || '$0.00'}</strong>
          </div>
        </div>

        <div className='about-links'>
          <a href='https://github.com' target='_blank' rel='noreferrer'>
            GitHub
          </a>
          <a href='https://docs.github.com' target='_blank' rel='noreferrer'>
            Documentation
          </a>
          <a href='https://github.com/issues' target='_blank' rel='noreferrer'>
            Report Bug
          </a>
        </div>

        <div className='about-actions'>
          <button onClick={onCheckUpdates}>Check for Updates</button>
          <button className='danger' onClick={onResetAll}>
            Reset All Settings
          </button>
        </div>
      </SettingsSection>
    </>
  )
}
