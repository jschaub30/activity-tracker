import { useEffect, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
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

export function ActivityPage() {
  const { id } = useParams<{ id: string }>()
  const [activity, setActivity] = useState<Activity | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [category, setCategory] = useState<ActivityCategory>('uncategorized')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    if (!id) return
    api<Activity>(`/api/activities/${id}`)
      .then((a) => {
        setActivity(a)
        setCategory(a.category)
      })
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed'))
  }, [id])

  async function onRelabel(e: FormEvent) {
    e.preventDefault()
    if (!id) return
    setSaved(false)
    const updated = await api<Activity>(`/api/activities/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ category, review_status: 'confirmed' }),
    })
    setActivity(updated)
    setSaved(true)
  }

  if (error) return <p className="error">{error}</p>
  if (!activity) return <p>Loading…</p>

  const isWeekSummaryType = (['run', 'hike', 'stair'] as const).some(
    (c) => activity.category === c || activity.suggested_category === c,
  )

  return (
    <div className="detail">
      <p>
        <Link to="/">← Week</Link> · <Link to="/review">Review</Link>
      </p>
      <h1>{activity.name || 'Activity'}</h1>
      <p className="muted">
        {new Date(activity.start_time).toLocaleString()} · Garmin:{' '}
        <code>{activity.garmin_type || '—'}</code>
      </p>

      <div className="stat-grid">
        {isWeekSummaryType ? (
          <>
            <div className="stat">
              <div className="stat-label">Distance</div>
              <div className="stat-value">{formatMi(activity.distance_mi)}</div>
            </div>
            <div className="stat">
              <div className="stat-label">Elevation gain</div>
              <div className="stat-value">{formatFt(activity.elevation_ft)}</div>
            </div>
          </>
        ) : null}
        <div className="stat">
          <div className="stat-label">Duration</div>
          <div className="stat-value">{formatDuration(activity.duration_s)}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Calories</div>
          <div className="stat-value">
            {activity.calories ?? activity.active_calories ?? '—'}
          </div>
        </div>
        {activity.avg_hr != null && (
          <div className="stat">
            <div className="stat-label">Avg HR</div>
            <div className="stat-value">{activity.avg_hr}</div>
          </div>
        )}
        {activity.max_hr != null && (
          <div className="stat">
            <div className="stat-label">Max HR</div>
            <div className="stat-value">{activity.max_hr}</div>
          </div>
        )}
      </div>

      <form className="relabel" onSubmit={onRelabel}>
        <h2>Re-label</h2>
        <label>
          Category
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value as ActivityCategory)}
          >
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" className="primary">
          Save &amp; confirm
        </button>
        {saved && <span className="ok">Saved</span>}
      </form>
    </div>
  )
}
