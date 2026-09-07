import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { formatCal } from '../lib/format'
import { useReloadWhenSyncFinishes } from '../lib/sync'
import { formatDistance, formatElevation, useUnits } from '../lib/units'
import type { MonthsList } from '../types'

export function MonthsPage() {
  const units = useUnits()
  const [data, setData] = useState<MonthsList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await api<MonthsList>('/api/months?count=24'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load months')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useReloadWhenSyncFinishes(load)

  if (loading && !data) return <p>Loading months…</p>
  if (error) return <p className="error">{error}</p>
  if (!data) return null

  return (
    <div className="week-page">
      <div className="week-header">
        <h1>Months</h1>
      </div>
      <div className="week-table-wrap">
        <table className="weeks-list-table">
          <thead>
            <tr>
              <th>Month</th>
              <th className="num">Distance</th>
              <th className="num">Elevation</th>
              <th className="num">Calories</th>
            </tr>
          </thead>
          <tbody>
            {data.months.map((m) => (
              <tr key={`${m.year}-${m.month}`} className={m.is_current ? 'current-week' : undefined}>
                <td>
                  <span className="week-label">
                    {m.label}
                    {m.is_current && <span className="badge-current">this month</span>}
                  </span>
                </td>
                <td className="num">{formatDistance(m.totals.distance_mi, units)}</td>
                <td className="num">{formatElevation(m.totals.elevation_ft, units)}</td>
                <td className="num">{formatCal(m.totals.calories)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
