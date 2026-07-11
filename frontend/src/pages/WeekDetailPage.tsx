import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { formatCal, formatFt, formatMi, weekdayLabel } from '../lib/format'
import type { WeekSummary } from '../types'

export function WeekDetailPage() {
  const { weekStart } = useParams<{ weekStart: string }>()
  const [week, setWeek] = useState<WeekSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!weekStart) return
    setLoading(true)
    api<WeekSummary>(`/api/weeks/detail?start=${weekStart}`)
      .then(setWeek)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [weekStart])

  if (loading) return <p>Loading week…</p>
  if (error) return <p className="error">{error}</p>
  if (!week) return null

  return (
    <div className="week-page">
      <p>
        <Link to="/">← All weeks</Link>
      </p>
      <div className="week-header">
        <div>
          <h1>
            {week.week_start} → {week.week_end}
          </h1>
          <p className="muted">
            {week.timezone} · runs, hikes &amp; stairs · mi / ft / cal
          </p>
        </div>
      </div>

      <div className="week-table-wrap">
        <table className="week-table">
          <thead>
            <tr>
              {week.days.map((d) => (
                <th key={d.date}>
                  <div>{weekdayLabel(d.date)}</div>
                  <div className="th-date">{d.date.slice(5)}</div>
                </th>
              ))}
              <th className="totals-col">Week total</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              {week.days.map((d) => (
                <td key={d.date}>
                  {d.activities.length === 0 ? (
                    <span className="empty">—</span>
                  ) : (
                    <ul className="act-list">
                      {d.activities.map((a) => (
                        <li key={a.id}>
                          <Link to={`/activities/${a.id}`}>
                            <span className={`badge ${a.category}`}>
                              {a.category}
                            </span>
                            <span className="act-name">{a.name || 'Activity'}</span>
                            <span className="act-stats">
                              {formatMi(a.distance_mi)} · {formatFt(a.elevation_ft)} ·{' '}
                              {formatCal(a.calories)}
                            </span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  )}
                </td>
              ))}
              <td className="totals-col">
                <div className="total-num">{formatMi(week.totals.distance_mi)}</div>
                <div className="total-num">{formatFt(week.totals.elevation_ft)}</div>
                <div className="total-num">{formatCal(week.totals.calories)}</div>
                <div className="muted small">combined runs + hikes + stairs</div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
