import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { AuthProvider, useAuth } from './lib/auth'
import { ActivityPage } from './pages/ActivityPage'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { ReviewPage } from './pages/ReviewPage'
import { SettingsPage } from './pages/SettingsPage'
import { WeekDetailPage } from './pages/WeekDetailPage'
import { WeekPage } from './pages/WeekPage'

function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  if (loading) return <p className="main">Loading…</p>
  if (!user) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route
            path="/"
            element={
              <Protected>
                <WeekPage />
              </Protected>
            }
          />
          <Route
            path="/weeks/:weekStart"
            element={
              <Protected>
                <WeekDetailPage />
              </Protected>
            }
          />
          <Route
            path="/review"
            element={
              <Protected>
                <ReviewPage />
              </Protected>
            }
          />
          <Route
            path="/activities/:id"
            element={
              <Protected>
                <ActivityPage />
              </Protected>
            }
          />
          <Route
            path="/settings"
            element={
              <Protected>
                <SettingsPage />
              </Protected>
            }
          />
        </Route>
      </Routes>
    </AuthProvider>
  )
}
