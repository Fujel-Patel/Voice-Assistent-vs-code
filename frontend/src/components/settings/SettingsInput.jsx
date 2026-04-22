import { useMemo, useState } from 'react'

export default function SettingsInput({
  label,
  type = 'text',
  value,
  onChange,
  validate,
  error,
  placeholder,
  rightSlot,
}) {
  const [visible, setVisible] = useState(false)
  const derivedError = useMemo(() => {
    if (error) return error
    if (!validate) return ''
    return validate(value) || ''
  }, [error, validate, value])

  const actualType = type === 'password' ? (visible ? 'text' : 'password') : type

  return (
    <label className='settings-control-column'>
      <span>{label}</span>
      <div className={`settings-input-wrap ${derivedError ? 'invalid' : ''}`}>
        <input
          type={actualType}
          value={value}
          placeholder={placeholder}
          aria-label={label}
          onChange={(event) => onChange?.(event.target.value)}
          className='settings-input'
        />
        {type === 'password' ? (
          <button type='button' className='settings-input-icon' onClick={() => setVisible((v) => !v)}>
            {visible ? 'Hide' : 'Show'}
          </button>
        ) : null}
        {rightSlot || null}
      </div>
      {derivedError ? <small className='settings-error'>{derivedError}</small> : null}
    </label>
  )
}
