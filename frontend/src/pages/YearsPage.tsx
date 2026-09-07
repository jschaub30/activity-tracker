import { useCallback, useEffect, useState } from 'react'
import { api } from '../api/client'
import { formatCal } from '../lib/format'
import { useReloadWhenSyncFinishes } from '../lib/sync'
import { formatDistance, formatElevation, useUnits } from '../lib/units'
import type { YearMonth, YearsList } from '../types'

const MONTH_ABBR = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
]

function MonthCell({ month }: { month: YearMonth }) {
  const units = useUnits()
  const empty =
    month.totals.distance_mi === 0 &&
    month.totals.elevation_ft === 0 &&
    month.totals.calories === 0
  return (
    <td className="day-col">
      {empty ? (
        <span className="empty">—</span>
      ) : (
        <>
          <div className="total-num">{formatDistance(month.totals.distance_mi, units)}</div>
          <div className="total-num">{formatElevation(month.totals.elevation_ft, units)}</div>
          <div className="total-num">{formatCal(month.totals.calories)}</div>
        </>
      )}
    </td>
  )
}

export function YearsPage() {
  const units = useUnits()
  const [data, setData] = useState<YearsList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await api<YearsList>('/api/years'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load years')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useReloadWhenSyncFinishes(load)

  if (loading && !data) return <p>Loading years…</p>
  if (error) return <p className="error">{error}</p>
  if (!data) return null

  return (
    <div className="week-page">
      <div className="week-header">
        <h1>Years</h1>
      </div>
      <div className="week-table-wrap">
        <table className="week-table stacked-weeks years-table">
          <thead>
            <tr>
              <th className="week-label-col">Year</th>
              {MONTH_ABBR.map((name) => (
                <th key={name} className="day-col">
                  {name}
                </th>
              ))}
              <th className="totals-col">Year total</th>
            </tr>
          </thead>
          <tbody>
            {data.years.map((y) => (
              <tr
                key={y.year}
                className={y.is_ytd ? 'current-week' : undefined}
              >
                <td className="week-label-col">
                  <div className="week-label">
                    {y.is_ytd ? (
                      <>
                        YTD
                        <span className="badge-current">{y.year}</span>
                      </>
                    ) : (
                      y.year
                    )}
                  </div>
                </td>
                {y.months.map((m) => (
                  <MonthCell key={m.month} month={m} />
                ))}
                <td className="totals-col">
                  <div className="total-num">
                    {formatDistance(y.totals.distance_mi, units)}
                  </div>
                  <div className="total-num">
                    {formatElevation(y.totals.elevation_ft, units)}
                  </div>
                  <div className="total-num">{formatCal(y.totals.calories)}</div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
