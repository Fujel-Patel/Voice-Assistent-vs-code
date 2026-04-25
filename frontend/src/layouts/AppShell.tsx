import { useEffect } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Home, Settings, User, LayoutDashboard } from 'lucide-react'
import { cn } from '../lib/utils'
import { useVoiceState } from '../hooks/useVoiceState'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAppStore } from '../store/appStore'

const NAV_LINKS = [
  { to: '/', label: 'HUD', icon: Home },
  { to: '/settings', label: 'Settings', icon: Settings },
  { to: '/voice-enrollment', label: 'Voice ID', icon: User },
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
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
    return () => { removeNavigate?.() }
  }, [navigate])

  useEffect(() => {
    let cancelled = false
    const setPermission = (next) => {
      if (!cancelled) setBrowserMicPermission(next)
    }
    const requestMicrophone = async () => {
      try {
        if (navigator.permissions?.query) {
          try {
            const status = await navigator.permissions.query({ name: 'microphone' })
            const mapState = (s) => s === 'granted' ? 'granted' : s === 'denied' ? 'denied' : 'unknown'
            setPermission(mapState(status.state))
            status.onchange = () => setPermission(mapState(status.state))
            if (status.state === 'denied') {
              addToast({ type: 'warning', title: 'Microphone permission needed', message: 'Please allow microphone access.' })
            }
          } catch { /* ignore */ }
        }
        if (window.jarvis?.media?.requestMicrophoneAccess) {
          const ok = await window.jarvis.media.requestMicrophoneAccess()
          setPermission(ok ? 'granted' : 'denied')
          if (!cancelled && !ok) addToast({ type: 'warning', title: 'Microphone permission needed', message: 'Please allow microphone access.' })
          return
        }
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        stream.getTracks().forEach((track) => track.stop())
        setPermission('granted')
      } catch {
        setPermission('denied')
        if (!cancelled) addToast({ type: 'warning', title: 'Microphone permission needed', message: 'Please allow microphone access.' })
      }
    }
    void requestMicrophone()
    return () => { cancelled = true }
  }, [addToast, setBrowserMicPermission])

  return (
    <div className="min-h-screen flex flex-col">
      <nav className="flex items-center justify-end gap-1 px-4 pt-2 bg-background/50 backdrop-blur-xl border-b border-white/5" aria-label="Primary navigation">
        {NAV_LINKS.map((item) => {
          const Icon = item.icon
          const isActive = location.pathname === item.to
          return (
            <Link
              key={item.to}
              to={item.to}
              className={cn(
                "flex items-center gap-1.5 px-3 py-2 rounded-t-lg text-xs font-mono tracking-widest uppercase transition-all duration-200",
                "text-muted-foreground hover:text-foreground hover:bg-white/5",
                isActive && "text-foreground bg-white/5"
              )}
            >
              <Icon className={cn("w-3.5 h-3.5", isActive && "text-cyan-400")} strokeWidth={isActive ? 2.5 : 2} />
              <span>{item.label}</span>
              {isActive && (
                <motion.div
                  layoutId="nav-indicator"
                  className="absolute bottom-0 left-0 right-0 h-0.5 bg-cyan-400"
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                />
              )}
            </Link>
          )
        })}
      </nav>
      <div className="flex-1 overflow-hidden">{children}</div>
    </div>
  )
}