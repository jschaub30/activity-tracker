import { useEffect, useState, type FormEvent } from 'react'
import { api } from '../api/client'
import type { GarminStatus, ShareLink, SyncStatus } from '../types'

interface ConnectResult extends GarminStatus {
  needs_mfa?: boolean
  message?: string | null
}

function absoluteShareUrl(path: string): string {
  return `${window.location.origin}${path}`
}

export function SettingsPage() {
  const [status, setStatus] = useState<GarminStatus | null>(null)
  const [sync, setSync] = useState<SyncStatus | null>(null)
  const [shares, setShares] = useState<ShareLink[]>([])
  const [shareLabel, setShareLabel] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mfaCode, setMfaCode] = useState('')
  const [needsMfa, setNeedsMfa] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function refresh() {
    setStatus(await api<GarminStatus>('/api/garmin/status'))
    setSync(await api<SyncStatus>('/api/sync/status'))
    setShares(await api<ShareLink[]>('/api/share'))
  }

  useEffect(() => {
    void refresh().catch((err) =>
      setError(err instanceof Error ? err.message : 'Failed to load settings'),
    )
  }, [])

  // Poll sync status while running
  useEffect(() => {
    if (!sync?.is_running && sync?.status !== 'running') return
    const t = setInterval(() => {
      void api<SyncStatus>('/api/sync/status')
        .then(setSync)
        .catch(() => undefined)
    }, 2000)
    return () => clearInterval(t)
  }, [sync?.is_running, sync?.status])

  async function onConnect(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setMessage(null)
    setBusy(true)
    try {
      const res = await api<ConnectResult>('/api/garmin/connect', {
        method: 'POST',
        body: JSON.stringify({ email, password }),
      })
      if (res.needs_mfa) {
        setNeedsMfa(true)
        setMessage(res.message ?? 'Enter your MFA code.')
        setStatus({
          connected: false,
          garmin_email: res.garmin_email,
        })
      } else {
        setNeedsMfa(false)
        setStatus(res)
        setPassword('')
        setMessage(res.message ?? 'Connected to Garmin.')
        await refresh()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Connect failed')
    } finally {
      setBusy(false)
    }
  }

  async function onMfa(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const res = await api<ConnectResult>('/api/garmin/mfa', {
        method: 'POST',
        body: JSON.stringify({ code: mfaCode }),
      })
      setNeedsMfa(false)
      setMfaCode('')
      setPassword('')
      setStatus(res)
      setMessage(res.message ?? 'Connected after MFA.')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'MFA failed')
    } finally {
      setBusy(false)
    }
  }

  async function onDisconnect() {
    await api('/api/garmin/connect', { method: 'DELETE' })
    setNeedsMfa(false)
    await refresh()
    setMessage('Disconnected')
  }

  async function onSync() {
    setError(null)
    setBusy(true)
    try {
      const res = await api<{ message: string }>('/api/sync', { method: 'POST' })
      setMessage(res.message)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setBusy(false)
    }
  }

  async function createShare(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const link = await api<ShareLink>('/api/share', {
        method: 'POST',
        body: JSON.stringify({ label: shareLabel || null }),
      })
      setShareLabel('')
      const url = absoluteShareUrl(link.path)
      try {
        await navigator.clipboard.writeText(url)
        setMessage(`Share link created and copied: ${url}`)
      } catch {
        setMessage(`Share link created: ${url}`)
      }
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create share link')
    } finally {
      setBusy(false)
    }
  }

  async function copyShare(path: string) {
    const url = absoluteShareUrl(path)
    try {
      await navigator.clipboard.writeText(url)
      setMessage(`Copied: ${url}`)
    } catch {
      setMessage(url)
    }
  }

  async function revokeShare(id: string) {
    setBusy(true)
    setError(null)
    try {
      await api(`/api/share/${id}`, { method: 'DELETE' })
      setMessage('Share link revoked')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not revoke link')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <h1>Settings</h1>
      <p className="muted">
        Local multi-user · timezone America/Denver · units mi/ft
      </p>

      {error && <p className="error">{error}</p>}
      {message && <p className="banner">{message}</p>}

      <section className="card">
        <h2>Share link (read-only)</h2>
        <p className="muted small">
          Anyone with the link can view your weekly summary and charts (confirmed
          runs, hikes, and stairs only). They cannot sync, edit, or see review
          data.
        </p>
        <form onSubmit={createShare} className="stack">
          <label>
            Optional label
            <input
              type="text"
              value={shareLabel}
              onChange={(e) => setShareLabel(e.target.value)}
              placeholder="e.g. Family"
              maxLength={120}
            />
          </label>
          <button type="submit" className="primary" disabled={busy}>
            Create share link
          </button>
        </form>
        {shares.length === 0 ? (
          <p className="muted" style={{ marginTop: '1rem' }}>
            No share links yet.
          </p>
        ) : (
          <table className="data-table" style={{ marginTop: '1rem' }}>
            <thead>
              <tr>
                <th>Label</th>
                <th>Link</th>
                <th>Created</th>
                <th>Status</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {shares.map((s) => {
                const url = absoluteShareUrl(s.path)
                const active = !s.revoked_at
                return (
                  <tr key={s.id}>
                    <td>{s.label || '—'}</td>
                    <td className="small">
                      <code className="share-url">{url}</code>
                    </td>
                    <td className="small">
                      {new Date(s.created_at).toLocaleString()}
                    </td>
                    <td>{active ? 'Active' : 'Revoked'}</td>
                    <td>
                      <div className="week-actions">
                        {active && (
                          <>
                            <button type="button" onClick={() => void copyShare(s.path)}>
                              Copy
                            </button>
                            <button
                              type="button"
                              onClick={() => void revokeShare(s.id)}
                              disabled={busy}
                            >
                              Revoke
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </section>

      <section className="card">
        <h2>Garmin Connect</h2>
        {status?.connected ? (
          <>
            <p>
              Connected as <strong>{status.garmin_email}</strong>
            </p>
            {status.last_success_at && (
              <p className="muted small">
                Last successful sync:{' '}
                {new Date(status.last_success_at).toLocaleString()}
              </p>
            )}
            {status.last_error && (
              <p className="error small">{status.last_error}</p>
            )}
            <div className="week-actions" style={{ marginTop: '0.75rem' }}>
              <button type="button" className="primary" onClick={onSync} disabled={busy}>
                Sync now
              </button>
              <button type="button" onClick={onDisconnect} disabled={busy}>
                Disconnect
              </button>
            </div>
          </>
        ) : (
          <p className="muted">Not connected — enter your Garmin credentials below.</p>
        )}

        {needsMfa ? (
          <form onSubmit={onMfa} className="stack">
            <p className="muted small">
              Garmin sent a multi-factor code (email or authenticator). Enter it
              here to finish login.
            </p>
            <label>
              MFA code
              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                required
              />
            </label>
            <button type="submit" className="primary" disabled={busy}>
              {busy ? 'Verifying…' : 'Submit MFA'}
            </button>
          </form>
        ) : (
          <form onSubmit={onConnect} className="stack">
            <label>
              Garmin email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="username"
              />
            </label>
            <label>
              Garmin password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="current-password"
              />
            </label>
            <button type="submit" className="primary" disabled={busy}>
              {busy ? 'Connecting…' : 'Connect Garmin'}
            </button>
          </form>
        )}
      </section>

      <section className="card">
        <h2>Last sync</h2>
        {sync?.id ? (
          <ul className="plain">
            <li>
              Status: <strong>{sync.status}</strong>
              {sync.is_running ? ' (running…)' : ''}
            </li>
            <li>Fetched: {sync.activities_fetched}</li>
            <li>Created: {sync.activities_created}</li>
            <li>Updated: {sync.activities_updated}</li>
            {sync.error && <li className="error">{sync.error}</li>}
          </ul>
        ) : (
          <p className="muted">No sync runs yet</p>
        )}
        <p className="muted small" style={{ marginTop: '0.75rem' }}>
          After a successful sync, open <strong>Review</strong> to confirm
          categories. Confirmed runs, hikes, and stairs appear on the week grid.
        </p>
      </section>
    </div>
  )
}
