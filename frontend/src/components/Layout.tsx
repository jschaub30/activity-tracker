import { Link, NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { useSync } from '../lib/sync'

export function Layout() {
  const { user, logout } = useAuth()
  const { sync } = useSync()
  const running = !!sync?.is_running || sync?.status === 'running'

  return (
    <div className="app-shell">
      <header className="topbar">
        <Link to="/" className="brand">
          Activity Tracker
        </Link>
        {user && (
          <nav className="nav">
            <NavLink to="/">Weeks</NavLink>
            <NavLink to="/months">Months</NavLink>
            <NavLink to="/years">Years</NavLink>
            <NavLink to="/charts">Charts</NavLink>
            <NavLink to="/settings">Settings</NavLink>
            <span className="user-email">{user.email}</span>
            <button type="button" className="linkish" onClick={logout}>
              Log out
            </button>
          </nav>
        )}
      </header>
      {user && running && (
        <div className="sync-banner" role="status">
          Syncing Garmin activities
          {sync?.activities_fetched
            ? ` — ${sync.activities_fetched} fetched`
            : '…'}
          . Totals update when it finishes.
        </div>
      )}
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
