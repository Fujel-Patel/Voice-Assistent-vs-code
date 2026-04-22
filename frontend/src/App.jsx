import { Navigate, Route, Routes } from 'react-router-dom'
import ErrorBoundary from './components/ErrorBoundary'
import AppShell from './layouts/AppShell'
import DashboardPage from './pages/DashboardPage'
import MainPage from './pages/MainPage'
import SettingsPage from './pages/SettingsPage'
import VoiceEnrollmentPage from './pages/VoiceEnrollmentPage'

export default function App() {
  return (
    <ErrorBoundary>
      <AppShell>
        <Routes>
          <Route path='/' element={<MainPage />} />
          <Route path='/settings' element={<SettingsPage />} />
          <Route path='/voice-enrollment' element={<VoiceEnrollmentPage />} />
          <Route path='/dashboard' element={<DashboardPage />} />
          <Route path='*' element={<Navigate to='/' replace />} />
        </Routes>
      </AppShell>
    </ErrorBoundary>
  )
}
