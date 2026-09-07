import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import { formatDuration, formatGarminType } from '../lib/format'
import { formatDistance, formatElevation, useUnits } from '../lib/units'
import type { Activity } from '../types'

export function ActivityPage() {
  const units = useUnits()
  const { id } = useParams<{ id: string }>()
  const [activity, setActivity] = useState<Activity | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    api<Activity>(`/api/activities/${id}`)
      .then(setActivity)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed'))
  }, [id])

  if (error) return <p className="error">{error}</p>
  if (!activity) return <p>Loading…</p>

  const typeLabel = formatGarminType(activity.garmin_type)
  const showDistance =
    activity.distance_mi != null && activity.distance_mi > 0
  const showElev =
    activity.elevation_ft != null && activity.elevation_ft > 0

  return (
    <div className="detail">
      <p>
        <Link to="/">← Weeks</Link>
      </p>
      <h1>{activity.name || typeLabel || 'Activity'}</h1>
      <p className="muted">
        {new Date(activity.start_time).toLocaleString()}
        {typeLabel ? ` · ${typeLabel}` : ''}
      </p>

      <div className="stat-grid">
        {showDistance && (
          <div className="stat">
            <div className="stat-label">Distance</div>
            <div className="stat-value">
              {formatDistance(activity.distance_mi, units)}
            </div>
          </div>
        )}
        {showElev && (
          <div className="stat">
            <div className="stat-label">Elevation gain</div>
            <div className="stat-value">
              {formatElevation(activity.elevation_ft, units)}
            </div>
          </div>
        )}
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
    </div>
  )
}
