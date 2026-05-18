import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import HelpPage from './pages/HelpPage'
import SettingsPage from './pages/SettingsPage'
import SharedReportPage from './pages/SharedReportPage'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter basename="/constellation-simulator">
      <Routes>
        {/* Public routes — no auth required */}
        <Route path="/shared/:token" element={<SharedReportPage />} />

        {/* Auth routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/help" element={<PrivateRoute><HelpPage /></PrivateRoute>} />
        <Route path="/settings" element={<PrivateRoute><SettingsPage /></PrivateRoute>} />
        <Route path="/*" element={<PrivateRoute><DashboardPage /></PrivateRoute>} />
      </Routes>
    </BrowserRouter>
  )
}
