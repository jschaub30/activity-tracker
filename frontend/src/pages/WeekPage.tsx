import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { formatCal, formatFt, formatMi, weekdayLabel } from '../lib/format'
import type { SyncStatus, WeekDay, WeekSummary, WeeksList } from '../types'

function formatWeekLabel(start: string, end: string): string {
  const s = new Date(start + 'T12:00:00')
  const e = new Date(end + 'T12:00:00')
  const opts: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }
  return `${s.toLocaleDateString('en-US', opts)} – ${e.toLocaleDateString('en-US', opts)}`
}

function DayCell({ day, readOnly }: { day: WeekDay; readOnly: boolean }) {
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
                  {formatMi(a.distance_mi)} · {formatFt(a.elevation_ft)} ·{' '}
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
        <div className="total-num">{formatMi(week.totals.distance_mi)}</div>
        <div className="total-num">{formatFt(week.totals.elevation_ft)}</div>
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
  const [data, setData] = useState<WeeksList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [syncMsg, setSyncMsg] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const weeksUrl = shareToken
    ? `/api/public/${shareToken}/weeks?count=52`
    : '/api/weeks?count=52'

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setData(await api<WeeksList>(weeksUrl))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load weeks')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload when share token changes
  }, [weeksUrl])

  async function triggerSync() {
    setSyncMsg(null)
    try {
      const started = await api<{ message: string }>('/api/sync', { method: 'POST' })
      setSyncMsg(started.message)
      for (let i = 0; i < 90; i++) {
        await new Promise((r) => setTimeout(r, 2000))
        const status = await api<SyncStatus>('/api/sync/status')
        if (!status.is_running && status.status !== 'running') {
          if (status.error) {
            setSyncMsg(status.error)
          } else {
            setSyncMsg(
              `Sync ${status.status}: ${status.activities_created} new, ${status.activities_updated} updated (${status.activities_fetched} fetched)`,
            )
          }
          await load()
          return
        }
        setSyncMsg('Sync running…')
      }
      setSyncMsg('Sync still running — check Settings for status')
      await load()
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
          <h1>Weekly summary{titleSuffix ? ` · ${titleSuffix}` : ''}</h1>
          <p className="muted">
            Last 52 weeks · runs, hikes &amp; stairs
            {readOnly ? ' · read-only' : ''}
          </p>
        </div>
        {!readOnly && (
          <div className="week-actions">
            <button type="button" className="primary" onClick={triggerSync}>
              Sync now
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
          <>Confirmed runs, hikes, and stair steppers only.</>
        ) : (
          <>
            Click an activity for details. Only confirmed runs, hikes, and stair
            steppers appear — review imports on the{' '}
            <Link to="/review">Review</Link> page.
          </>
        )}
      </p>
    </div>
  )
}
