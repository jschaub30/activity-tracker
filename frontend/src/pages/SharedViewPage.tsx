import { useEffect, useState } from 'react'
import { NavLink, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { UnitsProvider, type Units } from '../lib/units'
import { ChartsPage } from './ChartsPage'
import { MonthsPage } from './MonthsPage'
import { WeekPage } from './WeekPage'
import { YearsPage } from './YearsPage'

interface PublicMeta {
  label: string | null
  timezone: string
  owner_display: string
  units?: Units
}

export function SharedViewPage({
  mode,
}: {
  mode: 'weeks' | 'months' | 'years' | 'charts'
}) {
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
            Weeks
          </NavLink>
          <NavLink to={`/s/${token}/months`}>Months</NavLink>
          <NavLink to={`/s/${token}/years`}>Years</NavLink>
          <NavLink to={`/s/${token}/charts`}>Charts</NavLink>
        </nav>
      </div>
      <UnitsProvider units={meta.units ?? 'imperial'}>
        {mode === 'weeks' && (
          <WeekPage shareToken={token} titleSuffix={title} />
        )}
        {mode === 'months' && (
          <MonthsPage shareToken={token} titleSuffix={title} />
        )}
        {mode === 'years' && (
          <YearsPage shareToken={token} titleSuffix={title} />
        )}
        {mode === 'charts' && (
          <ChartsPage shareToken={token} titleSuffix={title} />
        )}
      </UnitsProvider>
    </div>
  )
}
