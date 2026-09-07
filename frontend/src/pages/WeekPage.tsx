import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { formatCal, weekdayLabel } from '../lib/format'
import { formatDistance, formatElevation, useUnits } from '../lib/units'
import { useReloadWhenSyncFinishes, useSync } from '../lib/sync'
import type { WeekDay, WeekSummary, WeeksList } from '../types'

function formatWeekLabel(start: string, end: string): string {
  const s = new Date(start + 'T12:00:00')
  const e = new Date(end + 'T12:00:00')
  const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }
  return `${s.toLocaleDateString('en-US', opts)} – ${e.toLocaleDateString('en-US', opts)}`
}

function DayCell({ day, readOnly }: { day: WeekDay; readOnly: boolean }) {
  const units = useUnits()
  return (
    <td className="day-col">
      <div className="th-date day-cell-date">{day.date.slice(5)}</div>
      {day.activities.length === 0 ? (
        <span className="empty">—</span>
      ) : (
        <ul className="act-list">
          {day.activities.map((a) => {
            const body = (
              <>
                <span className={`badge ${a.category}`}>{a.category}</span>
                <span className="act-name">{a.name || 'Activity'}</span>
                <span className="act-stats">
                  {formatDistance(a.distance_mi, units)} ·{' '}
                  {formatElevation(a.elevation_ft, units)} ·{' '}
                  {formatCal(a.calories)}
                </span>
              </>
            )
            return (
              <li key={a.id}>
                {readOnly ? (
                  <div className="act-static">{body}</div>
                ) : (
                  <Link to={`/activities/${a.id}`}>{body}</Link>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </td>
  )
}

function WeekRow({
  week,
  isCurrent,
  readOnly,
}: {
  week: WeekSummary
  isCurrent: boolean
  readOnly: boolean
}) {
  const units = useUnits()
  return (
    <tr className={isCurrent ? 'current-week' : undefined}>
      <td className="week-label-col">
        <div className="week-label">
          {formatWeekLabel(week.week_start, week.week_end)}
          {isCurrent && <span className="badge-current">this week</span>}
        </div>
      </td>
      {week.days.map((d) => (
        <DayCell key={d.date} day={d} readOnly={readOnly} />
      ))}
      <td className="totals-col">
        <div className="total-num">
          {formatDistance(week.totals.distance_mi, units)}
        </div>
        <div className="total-num">
          {formatElevation(week.totals.elevation_ft, units)}
        </div>
        <div className="total-num">{formatCal(week.totals.calories)}</div>
      </td>
    </tr>
  )
}

export function WeekPage({
  shareToken,
  titleSuffix,
}: {
  shareToken?: string
  titleSuffix?: string
} = {}) {
  const readOnly = Boolean(shareToken)
  const { sync, startSync } = useSync()
  const running = !!sync?.is_running || sync?.status === 'running'
  const [data, setData] = useState<WeeksList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [syncMsg, setSyncMsg] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const weeksUrl = shareToken
    ? `/api/public/${shareToken}/weeks?count=52`
    : '/api/weeks?count=52'

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await api<WeeksList>(weeksUrl))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load weeks')
    } finally {
      setLoading(false)
    }
  }, [weeksUrl])

  useEffect(() => {
    void load()
  }, [load])

  useReloadWhenSyncFinishes(load, !readOnly)

  async function onSync() {
    setSyncMsg(null)
    try {
      await startSync()
    } catch (err) {
      setSyncMsg(err instanceof Error ? err.message : 'Sync failed')
    }
  }

  if (loading && !data) return <p>Loading weeks…</p>
  if (error) return <p className="error">{error}</p>
  if (!data || data.weeks.length === 0) return null

  const dayHeaders = data.weeks[0].days

  return (
    <div className="week-page">
      <div className="week-header">
        <div>
          <h1>Weeks{titleSuffix ? ` · ${titleSuffix}` : ''}</h1>
        </div>
        {!readOnly && (
          <div className="week-actions">
            <button
              type="button"
              className="primary"
              onClick={() => void onSync()}
              disabled={running}
            >
              {running ? 'Syncing…' : 'Sync now'}
            </button>
          </div>
        )}
      </div>

      {syncMsg && <p className="banner">{syncMsg}</p>}

      <div className="week-table-wrap">
        <table className="week-table stacked-weeks">
          <thead>
            <tr>
              <th className="week-label-col">Week</th>
              {dayHeaders.map((d) => (
                <th
                  key={d.date.slice(0, 4) + weekdayLabel(d.date)}
                  className="day-col"
                >
                  <div>{weekdayLabel(d.date)}</div>
                </th>
              ))}
              <th className="totals-col">Week total</th>
            </tr>
          </thead>
          <tbody>
            {data.weeks.map((week, idx) => (
              <WeekRow
                key={week.week_start}
                week={week}
                isCurrent={idx === 0}
                readOnly={readOnly}
              />
            ))}
          </tbody>
        </table>
      </div>

      <p className="muted small">
        {readOnly ? (
          <>
            Confirmed activities only. Distance and elevation count runs, hikes,
            and stairs; calories count all confirmed activities.
          </>
        ) : (
          <>
            Click an activity for details. Distance and elevation count runs,
            hikes, and stairs; calories count all categories.
          </>
        )}
      </p>
    </div>
  )
}
