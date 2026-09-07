import { createContext, useContext, type ReactNode } from 'react'
import { useAuth } from './auth'

export type Units = 'imperial' | 'metric'

const KM_PER_MI = 1.609344
const M_PER_FT = 0.3048

const UnitsOverride = createContext<Units | null>(null)

export function UnitsProvider({
  units,
  children,
}: {
  units: Units
  children: ReactNode
}) {
  return <UnitsOverride.Provider value={units}>{children}</UnitsOverride.Provider>
}

export function useUnits(): Units {
  const override = useContext(UnitsOverride)
  const { user } = useAuth()
  return override ?? user?.units ?? 'imperial'
}

export function formatDistance(mi: number | null | undefined, units: Units): string {
  if (mi == null) return '—'
  if (units === 'metric') return `${(mi * KM_PER_MI).toFixed(2)} km`
  return `${mi.toFixed(2)} mi`
}

export function formatElevation(ft: number | null | undefined, units: Units): string {
  if (ft == null) return '—'
  if (units === 'metric') {
    return `${Math.round(ft * M_PER_FT).toLocaleString()} m`
  }
  return `${Math.round(ft).toLocaleString()} ft`
}

export function distanceChartValue(mi: number, units: Units): number {
  return units === 'metric' ? mi * KM_PER_MI : mi
}

export function elevationChartValue(ft: number, units: Units): number {
  return units === 'metric' ? ft * M_PER_FT : ft
}

export function distanceUnitLabel(units: Units): string {
  return units === 'metric' ? 'km' : 'mi'
}

export function elevationUnitLabel(units: Units): string {
  return units === 'metric' ? 'm' : 'ft'
}
