export type ActivityCategory =
  | 'run'
  | 'hike'
  | 'stair'
  | 'cardio'
  | 'strength'
  | 'uncategorized'

/** Categories shown on the week grid (combined distance + elevation). */
export const WEEK_SUMMARY_CATEGORIES: ActivityCategory[] = ['run', 'hike', 'stair']

export type ReviewStatus = 'pending' | 'confirmed'

export interface User {
  id: string
  email: string
  timezone: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Activity {
  id: string
  garmin_activity_id: string
  name: string
  start_time: string
  garmin_type: string
  suggested_category: ActivityCategory
  category: ActivityCategory
  review_status: ReviewStatus
  distance_m: number | null
  elevation_gain_m: number | null
  distance_mi: number | null
  elevation_ft: number | null
  duration_s: number | null
  active_calories: number | null
  avg_hr: number | null
  max_hr: number | null
  calories: number | null
}

export interface WeekActivity {
  id: string
  name: string
  category: ActivityCategory
  distance_mi: number
  elevation_ft: number
  calories: number
  duration_s: number | null
}

export interface WeekDay {
  date: string
  activities: WeekActivity[]
}

export interface WeekSummary {
  week_start: string
  week_end: string
  timezone: string
  days: WeekDay[]
  totals: {
    distance_mi: number
    elevation_ft: number
    calories: number
  }
}

/** Stacked week grid: full Sun–Sat detail per week, most recent first */
export interface WeeksList {
  timezone: string
  weeks: WeekSummary[]
}

export interface GarminStatus {
  connected: boolean
  garmin_email?: string | null
  connected_at?: string | null
  last_success_at?: string | null
  last_error?: string | null
}

export interface SyncStatus {
  id?: string | null
  status?: string | null
  started_at?: string | null
  finished_at?: string | null
  activities_fetched: number
  activities_created: number
  activities_updated: number
  error?: string | null
  is_running: boolean
}

export interface ShareLink {
  id: string
  token: string
  label: string | null
  created_at: string
  revoked_at: string | null
  path: string
}
