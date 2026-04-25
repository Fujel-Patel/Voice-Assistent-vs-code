import { Navigate, Route, Routes } from 'react-router-dom'
import { ThemeProvider } from './components/ThemeProvider'
import AppShell from './layouts/AppShell'
import MainPage from './pages/MainPage'
import SettingsPage from './pages/SettingsPage'
import VoiceEnrollmentPage from './pages/VoiceEnrollmentPage'
import DashboardPage from './pages/DashboardPage'

export default function App() {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="jarvis-theme">
      <AppShell>
        <Routes>
          <Route path='/' element={<MainPage />} />
          <Route path='/settings' element={<SettingsPage />} />
          <Route path='/voice-enrollment' element={<VoiceEnrollmentPage />} />
          <Route path='/dashboard' element={<DashboardPage />} />
          <Route path='*' element={<Navigate to='/' replace />} />
        </Routes>
      </AppShell>
    </ThemeProvider>
  )
}