import { useEffect } from 'react'
import { useAppStore } from '../store/appStore'

function ToastItem({ toast }) {
  const removeToast = useAppStore((state) => state.removeToast)

  useEffect(() => {
    const timeout = setTimeout(() => removeToast(toast.id), 3500)
    return () => clearTimeout(timeout)
  }, [removeToast, toast.id])

  return (
    <div className={`toast ${toast.type || 'info'}`}>
      <strong>{toast.title || 'Notice'}</strong>
      <p>{toast.message}</p>
    </div>
  )
}

export default function ToastHost() {
  const toasts = useAppStore((state) => state.toasts)

  return (
    <div className='toast-stack'>
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} />
      ))}
    </div>
  )
}
