export default function SettingsSection({ title, description, children, danger = false }) {
  return (
    <section className={`settings-section ${danger ? 'danger' : ''}`}>
      <header className='settings-section-header'>
        <h3>{title}</h3>
        {description ? <p>{description}</p> : null}
      </header>
      <div className='settings-section-body'>{children}</div>
    </section>
  )
}
