import { useEffect, useState } from 'react'
import { NavLink, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { ChartsPage } from './ChartsPage'
import { WeekPage } from './WeekPage'

interface PublicMeta {
  label: string | null
  timezone: string
  owner_display: string
}

export function SharedViewPage({ mode }: { mode: 'weeks' | 'charts' }) {
  const { token } = useParams<{ token: string }>()
  const [meta, setMeta] = useState<PublicMeta | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    api<PublicMeta>(`/api/public/${token}`)
      .then(setMeta)
      .catch((err) =>
        setError(err instanceof Error ? err.message : 'Invalid or revoked share link'),
      )
  }, [token])

  if (!token) return <p className="error">Missing share token</p>
  if (error) return <p className="error">{error}</p>
  if (!meta) return <p>Loading shared view…</p>

  const title =
    meta.label?.trim() ||
    `${meta.owner_display}'s activities`

  return (
    <div className="shared-view">
      <div className="shared-banner">
        <div>
          <strong>{title}</strong>
          <span className="muted small"> · shared read-only link</span>
        </div>
        <nav className="nav shared-nav">
          <NavLink to={`/s/${token}`} end>
            Week
          </NavLink>
          <NavLink to={`/s/${token}/charts`}>Charts</NavLink>
        </nav>
      </div>
      {mode === 'weeks' ? (
        <WeekPage shareToken={token} titleSuffix={title} />
      ) : (
        <ChartsPage shareToken={token} titleSuffix={title} />
      )}
    </div>
  )
}
