import { Link, NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../lib/auth'

export function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand">
          Garmin Activity Tracker
        </Link>
        {user && (
          <nav className="nav">
            <NavLink to="/">Week</NavLink>
            <NavLink to="/charts">Charts</NavLink>
            <NavLink to="/review">Review</NavLink>
            <NavLink to="/settings">Settings</NavLink>
            <span className="user-email">{user.email}</span>
            <button type="button" className="linkish" onClick={logout}>
              Log out
            </button>
          </nav>
        )}
      </header>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
