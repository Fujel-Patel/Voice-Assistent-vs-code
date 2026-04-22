const NAV = [
  { id: 'general', icon: '[G]', label: 'General' },
  { id: 'voice', icon: '[V]', label: 'Voice & Audio' },
  { id: 'api', icon: '[K]', label: 'API Keys' },
  { id: 'ai', icon: '[AI]', label: 'AI & Brain' },
  { id: 'about', icon: '[i]', label: 'About' },
  { id: 'appearance', icon: '[UI]', label: 'Appearance' },
]

export default function SettingsSidebar({ active, onChange }) {
  return (
    <aside className='settings-sidebar'>
      {NAV.map((item) => (
        <button
          key={item.id}
          type='button'
          onClick={() => onChange?.(item.id)}
          className={`settings-nav-item ${active === item.id ? 'active' : ''}`}
        >
          <span className='icon'>{item.icon}</span>
          <span>{item.label}</span>
        </button>
      ))}
    </aside>
  )
}
