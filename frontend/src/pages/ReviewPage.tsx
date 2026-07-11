import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { formatDuration, formatFt, formatMi } from '../lib/format'
import type { Activity, ActivityCategory } from '../types'

const CATEGORIES: ActivityCategory[] = [
  'run',
  'hike',
  'stair',
  'cardio',
  'strength',
  'uncategorized',
]

export function ReviewPage() {
  const [items, setItems] = useState<Activity[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setItems(await api<Activity[]>('/api/activities/review'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  async function setCategory(id: string, category: ActivityCategory) {
    await api(`/api/activities/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ category, review_status: 'confirmed' }),
    })
    await load()
  }

  async function bulkConfirm() {
    await api('/api/activities/bulk-confirm', {
      method: 'POST',
      body: JSON.stringify({ accept_suggested: true }),
    })
    await load()
  }

  if (loading) return <p>Loading review queue…</p>
  if (error) return <p className="error">{error}</p>

  return (
    <div>
      <div className="week-header">
        <div>
          <h1>Review queue</h1>
          <p className="muted">
            Confirm or re-label activities before they count on the week grid.
          </p>
        </div>
        {items.length > 0 && (
          <button type="button" className="primary" onClick={bulkConfirm}>
            Accept all suggestions
          </button>
        )}
      </div>

      {items.length === 0 ? (
        <p className="muted">Nothing pending. Sync Garmin data to import activities.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>When</th>
              <th>Name</th>
              <th>Garmin type</th>
              <th>Suggested</th>
              <th>Metrics</th>
              <th>Set category</th>
            </tr>
          </thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.id}>
                <td>{new Date(a.start_time).toLocaleString()}</td>
                <td>
                  <Link to={`/activities/${a.id}`}>{a.name || 'Activity'}</Link>
                </td>
                <td>
                  <code>{a.garmin_type || '—'}</code>
                </td>
                <td>
                  <span className={`badge ${a.suggested_category}`}>
                    {a.suggested_category}
                  </span>
                </td>
                <td className="small">
                  {a.category === 'cardio' ||
                  a.suggested_category === 'cardio' ||
                  a.category === 'strength' ||
                  a.suggested_category === 'strength' ? (
                    <>
                      {formatDuration(a.duration_s)} ·{' '}
                      {a.calories ?? a.active_calories ?? '—'} cal
                    </>
                  ) : (
                    <>
                      {formatMi(a.distance_mi)} · {formatFt(a.elevation_ft)}
                    </>
                  )}
                </td>
                <td>
                  <select
                    defaultValue=""
                    onChange={(e) => {
                      const v = e.target.value as ActivityCategory
                      if (v) void setCategory(a.id, v)
                    }}
                  >
                    <option value="" disabled>
                      Choose…
                    </option>
                    {CATEGORIES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
