import { Navigate, Route, Routes } from 'react-router-dom'
import { ThemeProvider } from './components/ThemeProvider'
import AppShell from './layouts/AppShell'
import { lazy, Suspense } from 'react'

const MainPage = lazy(() => import('./pages/MainPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const VoiceEnrollmentPage = lazy(() => import('./pages/VoiceEnrollmentPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))

export default function App() {
  return (
    <AppShell>
      <Suspense fallback={<div className="flex items-center justify-center h-full">Loading…</div>}>
        <Routes>
          <Route path='/' element={<MainPage />} />
          <Route path='/settings' element={<SettingsPage />} />
          <Route path='/voice-enrollment' element={<VoiceEnrollmentPage />} />
          <Route path='/dashboard' element={<DashboardPage />} />
          <Route path='*' element={<Navigate to='/' replace />} />
        </Routes>
      </Suspense>
    </AppShell>
  )
}