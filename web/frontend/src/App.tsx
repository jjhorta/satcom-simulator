import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ConsentBanner from './components/ConsentBanner'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import DashboardPage from './pages/DashboardPage'
import HelpPage from './pages/HelpPage'
import SettingsPage from './pages/SettingsPage'
import SharedReportPage from './pages/SharedReportPage'
import AdminPage from './pages/AdminPage'
import TeamPage from './pages/TeamPage'
import BillingPage from './pages/BillingPage'
import BatchPage      from './pages/BatchPage'
import CopilotPage    from './pages/CopilotPage'
import DemandPage     from './pages/DemandPage'
import ShapesPage     from './pages/ShapesPage'
import MaritimePage   from './pages/MaritimePage'

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
        <Route path="/login"    element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/help"     element={<PrivateRoute><HelpPage /></PrivateRoute>} />
        <Route path="/settings" element={<PrivateRoute><SettingsPage /></PrivateRoute>} />
        <Route path="/admin"    element={<PrivateRoute><AdminPage /></PrivateRoute>} />
        <Route path="/team"     element={<PrivateRoute><TeamPage /></PrivateRoute>} />
        <Route path="/billing"  element={<PrivateRoute><BillingPage /></PrivateRoute>} />
        <Route path="/batch"   element={<PrivateRoute><BatchPage /></PrivateRoute>} />
        <Route path="/carl"    element={<PrivateRoute><CopilotPage /></PrivateRoute>} />
        <Route path="/demand"  element={<PrivateRoute><DemandPage /></PrivateRoute>} />
        <Route path="/shapes"  element={<PrivateRoute><ShapesPage /></PrivateRoute>} />
        <Route path="/maritime" element={<PrivateRoute><MaritimePage /></PrivateRoute>} />
        <Route path="/*"        element={<PrivateRoute><DashboardPage /></PrivateRoute>} />
      </Routes>
    <ConsentBanner />
  </BrowserRouter>
  )
}
