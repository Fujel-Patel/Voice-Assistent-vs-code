import { useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useVoiceState } from '../hooks/useVoiceState'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAppStore } from '../store/appStore'

const NAV_LINKS = [
  { to: '/', label: 'HUD', icon: '◉' },
  { to: '/settings', label: 'SETTINGS', icon: '⚙' },
  { to: '/voice-enrollment', label: 'VOICE ID', icon: '◈' },
  { to: '/dashboard', label: 'DASHBOARD', icon: '▦' },
]

export default function AppShell({ children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const setLastRoute = useAppStore((state) => state.setLastRoute)
  const addToast = useAppStore((state) => state.addToast)
  const setBrowserMicPermission = useAppStore((state) => state.setBrowserMicPermission)
  const websocket = useWebSocket()

  useVoiceState(websocket)

  useEffect(() => {
    setLastRoute(location.pathname)
  }, [location.pathname, setLastRoute])

  useEffect(() => {
    const removeNavigate = window.jarvis?.onNavigate?.((route) => {
      if (!route || typeof route !== 'string') return
      navigate(route)
    })

    return () => {
      removeNavigate?.()
    }
  }, [navigate])

  useEffect(() => {
    let cancelled = false

    const setPermission = (next) => {
      if (!cancelled) {
        setBrowserMicPermission(next)
      }
    }

    const requestMicrophone = async () => {
      try {
        if (navigator.permissions?.query) {
          try {
            const status = await navigator.permissions.query({ name: 'microphone' })
            const mapState = (state) => {
              if (state === 'granted') return 'granted'
              if (state === 'denied') return 'denied'
              return 'unknown'
            }

            setPermission(mapState(status.state))

            status.onchange = () => {
              setPermission(mapState(status.state))
            }

            if (status.state === 'denied') {
              addToast({
                type: 'warning',
                title: 'Microphone permission needed',
                message: 'Please allow microphone access for realtime voice capture.',
              })
              return
            }
          } catch {
            // Ignore permission API failures and continue with active probe.
          }
        }

        if (window.jarvis?.media?.requestMicrophoneAccess) {
          const ok = await window.jarvis.media.requestMicrophoneAccess()
          setPermission(ok ? 'granted' : 'denied')
          if (!cancelled && !ok) {
            addToast({
              type: 'warning',
              title: 'Microphone permission needed',
              message: 'Please allow microphone access for realtime voice capture.',
            })
          }
          return
        }

        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        stream.getTracks().forEach((track) => track.stop())
        setPermission('granted')
      } catch {
        setPermission('denied')
        if (!cancelled) {
          addToast({
            type: 'warning',
            title: 'Microphone permission needed',
            message: 'Please allow microphone access for realtime voice capture.',
          })
        }
      }
    }

    void requestMicrophone()

    return () => {
      cancelled = true
    }
  }, [addToast, setBrowserMicPermission])

  return (
    <div className='app-shell'>
      <nav className='app-route-nav' aria-label='Primary navigation'>
        {NAV_LINKS.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={`app-route-link ${location.pathname === item.to ? 'active' : ''}`}
          >
            <span className='app-route-link-icon' aria-hidden='true'>
              {item.icon}
            </span>
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>
      <div className='app-shell-content'>{children}</div>
    </div>
  )
}
