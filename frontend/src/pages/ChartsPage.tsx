import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from '../api/client'
import { formatCal } from '../lib/format'
import {
  distanceChartValue,
  distanceUnitLabel,
  elevationChartValue,
  elevationUnitLabel,
  formatDistance,
  formatElevation,
  useUnits,
} from '../lib/units'
import { useReloadWhenSyncFinishes } from '../lib/sync'
import type { WeeksList } from '../types'

interface ChartPoint {
  weekStart: string
  label: string
  distance: number
  elevation: number
  calories: number
}

function weekLabel(iso: string): string {
  const d = new Date(iso + 'T12:00:00')
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const tooltipStyle = {
  background: '#1a2332',
  border: '1px solid #2a3a4f',
  borderRadius: 8,
  color: '#e8eef5',
}

function MetricChart({
  title,
  data,
  dataKey,
  color,
  formatY,
  formatTip,
}: {
  title: string
  data: ChartPoint[]
  dataKey: keyof ChartPoint
  color: string
  formatY: (n: number) => string
  formatTip: (n: number) => string
}) {
  return (
    <section className="card chart-card">
      <h2>{title}</h2>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
            <CartesianGrid stroke="#2a3a4f" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: '#8b9cb3', fontSize: 11 }}
              interval="preserveStartEnd"
              minTickGap={28}
            />
            <YAxis
              tick={{ fill: '#8b9cb3', fontSize: 11 }}
              width={56}
              tickFormatter={(v: number) => formatY(v)}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              labelStyle={{ color: '#8b9cb3' }}
              cursor={{ fill: 'rgba(61, 156, 240, 0.08)' }}
              formatter={(value) => [formatTip(Number(value ?? 0)), title]}
              labelFormatter={(_, payload) => {
                const p = payload?.[0]?.payload as ChartPoint | undefined
                return p ? `Week of ${p.label}` : ''
              }}
            />
            <Bar dataKey={dataKey} fill={color} radius={[2, 2, 0, 0]} maxBarSize={14} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  )
}

export function ChartsPage({
  shareToken,
  titleSuffix,
}: {
  shareToken?: string
  titleSuffix?: string
} = {}) {
  const readOnly = Boolean(shareToken)
  const units = useUnits()
  const [data, setData] = useState<WeeksList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const weeksUrl = shareToken
    ? `/api/public/${shareToken}/weeks?count=52`
    : '/api/weeks?count=52'

  const load = useCallback(() => {
    setLoading(true)
    api<WeeksList>(weeksUrl)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [weeksUrl])

  useEffect(() => {
    load()
  }, [load])

  useReloadWhenSyncFinishes(load, !readOnly)

  const points = useMemo<ChartPoint[]>(() => {
    if (!data) return []
    // API returns most recent first; chart left→right oldest→newest
    return [...data.weeks]
      .reverse()
      .map((w) => ({
        weekStart: w.week_start,
        label: weekLabel(w.week_start),
        distance: distanceChartValue(w.totals.distance_mi, units),
        elevation: elevationChartValue(w.totals.elevation_ft, units),
        calories: w.totals.calories,
      }))
  }, [data, units])

  const yearTotals = useMemo(() => {
    return (data?.weeks ?? []).reduce(
      (acc, w) => ({
        distance_mi: acc.distance_mi + w.totals.distance_mi,
        elevation_ft: acc.elevation_ft + w.totals.elevation_ft,
        calories: acc.calories + w.totals.calories,
      }),
      { distance_mi: 0, elevation_ft: 0, calories: 0 },
    )
  }, [data])

  if (loading) return <p>Loading charts…</p>
  if (error) return <p className="error">{error}</p>
  if (!data) return null

  return (
    <div className="charts-page">
      <div className="week-header">
        <div>
          <h1>Year charts{titleSuffix ? ` · ${titleSuffix}` : ''}</h1>
          <p className="muted">Weekly totals</p>
        </div>
      </div>

      <div className="stat-grid year-totals">
        <div className="stat">
          <div className="stat-label">52-week distance</div>
          <div className="stat-value">
            {formatDistance(yearTotals.distance_mi, units)}
          </div>
        </div>
        <div className="stat">
          <div className="stat-label">52-week elevation</div>
          <div className="stat-value">
            {formatElevation(yearTotals.elevation_ft, units)}
          </div>
        </div>
        <div className="stat">
          <div className="stat-label">52-week calories</div>
          <div className="stat-value">{formatCal(yearTotals.calories)}</div>
        </div>
      </div>

      <MetricChart
        title={`Distance (${distanceUnitLabel(units)})`}
        data={points}
        dataKey="distance"
        color="#3d9cf0"
        formatY={(n) => (n >= 10 ? n.toFixed(0) : n.toFixed(1))}
        formatTip={(n) =>
          units === 'metric' ? `${n.toFixed(2)} km` : `${n.toFixed(2)} mi`
        }
      />
      <MetricChart
        title={`Elevation (${elevationUnitLabel(units)})`}
        data={points}
        dataKey="elevation"
        color="#7fd99a"
        formatY={(n) => Math.round(n).toLocaleString()}
        formatTip={(n) =>
          units === 'metric'
            ? `${Math.round(n).toLocaleString()} m`
            : `${Math.round(n).toLocaleString()} ft`
        }
      />
      <MetricChart
        title="Calories"
        data={points}
        dataKey="calories"
        color="#f0a06a"
        formatY={(n) => Math.round(n).toLocaleString()}
        formatTip={(n) => formatCal(n)}
      />

      <p className="muted small">
        Same confirmed activities as the{' '}
        <Link to={shareToken ? `/s/${shareToken}` : '/'}>weekly summary</Link>.
        Empty weeks plot as zero.
      </p>
    </div>
  )
}
