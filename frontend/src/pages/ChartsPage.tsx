import { useEffect, useMemo, useState } from 'react'
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
import { formatCal, formatFt, formatMi } from '../lib/format'
import type { WeeksList } from '../types'

interface ChartPoint {
  weekStart: string
  label: string
  distance_mi: number
  elevation_ft: number
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

export function ChartsPage() {
  const [data, setData] = useState<WeeksList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api<WeeksList>('/api/weeks?count=52')
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [])

  const points = useMemo<ChartPoint[]>(() => {
    if (!data) return []
    // API returns most recent first; chart left→right oldest→newest
    return [...data.weeks]
      .reverse()
      .map((w) => ({
        weekStart: w.week_start,
        label: weekLabel(w.week_start),
        distance_mi: w.totals.distance_mi,
        elevation_ft: w.totals.elevation_ft,
        calories: w.totals.calories,
      }))
  }, [data])

  const yearTotals = useMemo(() => {
    return points.reduce(
      (acc, p) => ({
        distance_mi: acc.distance_mi + p.distance_mi,
        elevation_ft: acc.elevation_ft + p.elevation_ft,
        calories: acc.calories + p.calories,
      }),
      { distance_mi: 0, elevation_ft: 0, calories: 0 },
    )
  }, [points])

  if (loading) return <p>Loading charts…</p>
  if (error) return <p className="error">{error}</p>
  if (!data) return null

  return (
    <div className="charts-page">
      <div className="week-header">
        <div>
          <h1>Year charts</h1>
          <p className="muted">
            Weekly totals · past 52 weeks · {data.timezone} · runs, hikes &amp;
            stairs
          </p>
        </div>
      </div>

      <div className="stat-grid year-totals">
        <div className="stat">
          <div className="stat-label">52-week distance</div>
          <div className="stat-value">{formatMi(yearTotals.distance_mi)}</div>
        </div>
        <div className="stat">
          <div className="stat-label">52-week elevation</div>
          <div className="stat-value">{formatFt(yearTotals.elevation_ft)}</div>
        </div>
        <div className="stat">
          <div className="stat-label">52-week calories</div>
          <div className="stat-value">{formatCal(yearTotals.calories)}</div>
        </div>
      </div>

      <MetricChart
        title="Distance (mi)"
        data={points}
        dataKey="distance_mi"
        color="#3d9cf0"
        formatY={(n) => (n >= 10 ? n.toFixed(0) : n.toFixed(1))}
        formatTip={(n) => formatMi(n)}
      />
      <MetricChart
        title="Elevation (ft)"
        data={points}
        dataKey="elevation_ft"
        color="#7fd99a"
        formatY={(n) => Math.round(n).toLocaleString()}
        formatTip={(n) => formatFt(n)}
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
        <Link to="/">weekly summary</Link>. Empty weeks plot as zero.
      </p>
    </div>
  )
}
