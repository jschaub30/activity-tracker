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
import { useReloadWhenSyncFinishes } from '../lib/sync'
import {
  distanceChartValue,
  distanceUnitLabel,
  elevationChartValue,
  elevationUnitLabel,
  formatDistance,
  formatElevation,
  useUnits,
} from '../lib/units'
import type { MonthsList, WeeksList, YearsList } from '../types'

type ChartRange = 'weeks' | 'months' | 'years'

interface ChartPoint {
  key: string
  label: string
  distance: number
  elevation: number
  calories: number
}

interface Totals {
  distance_mi: number
  elevation_ft: number
  calories: number
}

const RANGE_OPTIONS: { id: ChartRange; label: string }[] = [
  { id: 'weeks', label: '52 weeks' },
  { id: 'months', label: '24 months' },
  { id: 'years', label: 'All years' },
]

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
  periodWord,
}: {
  title: string
  data: ChartPoint[]
  dataKey: keyof ChartPoint
  color: string
  formatY: (n: number) => string
  formatTip: (n: number) => string
  periodWord: string
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
                return p ? `${periodWord} ${p.label}` : ''
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
  const [range, setRange] = useState<ChartRange>('weeks')
  const [points, setPoints] = useState<ChartPoint[] | null>(null)
  const [totals, setTotals] = useState<Totals>({
    distance_mi: 0,
    elevation_ft: 0,
    calories: 0,
  })
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const prefix = shareToken ? `/api/public/${shareToken}` : '/api'

  const load = useCallback(() => {
    setLoading(true)
    setError(null)
    const run = async () => {
      if (range === 'weeks') {
        const data = await api<WeeksList>(`${prefix}/weeks?count=52`)
        const weeks = [...data.weeks].reverse()
        setPoints(
          weeks.map((w) => ({
            key: w.week_start,
            label: weekLabel(w.week_start),
            distance: distanceChartValue(w.totals.distance_mi, units),
            elevation: elevationChartValue(w.totals.elevation_ft, units),
            calories: w.totals.calories,
          })),
        )
        setTotals(
          weeks.reduce(
            (acc, w) => ({
              distance_mi: acc.distance_mi + w.totals.distance_mi,
              elevation_ft: acc.elevation_ft + w.totals.elevation_ft,
              calories: acc.calories + w.totals.calories,
            }),
            { distance_mi: 0, elevation_ft: 0, calories: 0 },
          ),
        )
        return
      }
      if (range === 'months') {
        const data = await api<MonthsList>(`${prefix}/months?count=24`)
        const months = [...data.months].reverse()
        setPoints(
          months.map((m) => ({
            key: `${m.year}-${m.month}`,
            label: m.label,
            distance: distanceChartValue(m.totals.distance_mi, units),
            elevation: elevationChartValue(m.totals.elevation_ft, units),
            calories: m.totals.calories,
          })),
        )
        setTotals(
          months.reduce(
            (acc, m) => ({
              distance_mi: acc.distance_mi + m.totals.distance_mi,
              elevation_ft: acc.elevation_ft + m.totals.elevation_ft,
              calories: acc.calories + m.totals.calories,
            }),
            { distance_mi: 0, elevation_ft: 0, calories: 0 },
          ),
        )
        return
      }
      const data = await api<YearsList>(`${prefix}/years`)
      const years = [...data.years].reverse()
      setPoints(
        years.map((y) => ({
          key: String(y.year),
          label: y.is_ytd ? `YTD ${y.year}` : String(y.year),
          distance: distanceChartValue(y.totals.distance_mi, units),
          elevation: elevationChartValue(y.totals.elevation_ft, units),
          calories: y.totals.calories,
        })),
      )
      setTotals(
        years.reduce(
          (acc, y) => ({
            distance_mi: acc.distance_mi + y.totals.distance_mi,
            elevation_ft: acc.elevation_ft + y.totals.elevation_ft,
            calories: acc.calories + y.totals.calories,
          }),
          { distance_mi: 0, elevation_ft: 0, calories: 0 },
        ),
      )
    }
    run()
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [prefix, range, units])

  useEffect(() => {
    load()
  }, [load])

  useReloadWhenSyncFinishes(load, !readOnly)

  const subtitle =
    range === 'weeks'
      ? 'Weekly totals'
      : range === 'months'
        ? 'Monthly totals'
        : 'Yearly totals'
  const periodWord =
    range === 'weeks' ? 'Week of' : range === 'months' ? 'Month of' : 'Year'
  const statPrefix =
    range === 'weeks' ? '52-week' : range === 'months' ? '24-month' : 'All-years'

  const chartData = useMemo(() => points ?? [], [points])

  if (loading || !points) return <p>Loading charts…</p>
  if (error) return <p className="error">{error}</p>
  if (!points) return null

  return (
    <div className="charts-page">
      <div className="week-header">
        <div>
          <h1>Charts{titleSuffix ? ` · ${titleSuffix}` : ''}</h1>
          <p className="muted">{subtitle}</p>
        </div>
        <div className="range-toggle" role="group" aria-label="Chart range">
          {RANGE_OPTIONS.map((opt) => (
            <button
              key={opt.id}
              type="button"
              className={range === opt.id ? 'active' : undefined}
              onClick={() => setRange(opt.id)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      <div className="stat-grid year-totals">
        <div className="stat">
          <div className="stat-label">{statPrefix} distance</div>
          <div className="stat-value">
            {formatDistance(totals.distance_mi, units)}
          </div>
        </div>
        <div className="stat">
          <div className="stat-label">{statPrefix} elevation</div>
          <div className="stat-value">
            {formatElevation(totals.elevation_ft, units)}
          </div>
        </div>
        <div className="stat">
          <div className="stat-label">{statPrefix} calories</div>
          <div className="stat-value">{formatCal(totals.calories)}</div>
        </div>
      </div>

      <MetricChart
        title={`Distance (${distanceUnitLabel(units)})`}
        data={chartData}
        dataKey="distance"
        color="#3d9cf0"
        periodWord={periodWord}
        formatY={(n) => (n >= 10 ? n.toFixed(0) : n.toFixed(1))}
        formatTip={(n) =>
          units === 'metric' ? `${n.toFixed(2)} km` : `${n.toFixed(2)} mi`
        }
      />
      <MetricChart
        title={`Elevation (${elevationUnitLabel(units)})`}
        data={chartData}
        dataKey="elevation"
        color="#7fd99a"
        periodWord={periodWord}
        formatY={(n) => Math.round(n).toLocaleString()}
        formatTip={(n) =>
          units === 'metric'
            ? `${Math.round(n).toLocaleString()} m`
            : `${Math.round(n).toLocaleString()} ft`
        }
      />
      <MetricChart
        title="Calories"
        data={chartData}
        dataKey="calories"
        color="#f0a06a"
        periodWord={periodWord}
        formatY={(n) => Math.round(n).toLocaleString()}
        formatTip={(n) => formatCal(n)}
      />

      <p className="muted small">
        Same activities as{' '}
        <Link
          to={
            shareToken
              ? `/s/${shareToken}`
              : range === 'months'
                ? '/months'
                : range === 'years'
                  ? '/years'
                  : '/'
          }
        >
          {range === 'months' ? 'Months' : range === 'years' ? 'Years' : 'Weeks'}
        </Link>
        . Empty periods plot as zero.
      </p>
    </div>
  )
}
