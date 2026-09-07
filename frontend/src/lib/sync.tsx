import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'
import { api } from '../api/client'
import type { SyncStatus } from '../types'
import { useAuth } from './auth'

interface SyncStartResult {
  message: string
  sync_run_id: string
}

interface SyncCtx {
  sync: SyncStatus | null
  refresh: () => Promise<void>
  startSync: () => Promise<SyncStartResult>
}

const SyncContext = createContext<SyncCtx | null>(null)

export function SyncProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [sync, setSync] = useState<SyncStatus | null>(null)

  const refresh = useCallback(async () => {
    if (!user) {
      setSync(null)
      return
    }
    const next = await api<SyncStatus>('/api/sync/status')
    setSync(next)
  }, [user])

  useEffect(() => {
    void refresh().catch(() => undefined)
  }, [refresh])

  const running = !!sync?.is_running || sync?.status === 'running'
  useEffect(() => {
    if (!user) return
    const ms = running ? 2000 : 20000
    const t = setInterval(() => {
      void refresh().catch(() => undefined)
    }, ms)
    return () => clearInterval(t)
  }, [user, running, refresh])

  const startSync = useCallback(async () => {
    const res = await api<SyncStartResult>('/api/sync', { method: 'POST' })
    setSync((prev) => ({
      id: res.sync_run_id,
      status: 'running',
      activities_fetched: prev?.activities_fetched ?? 0,
      activities_created: prev?.activities_created ?? 0,
      activities_updated: prev?.activities_updated ?? 0,
      is_running: true,
      error: null,
    }))
    void refresh().catch(() => undefined)
    return res
  }, [refresh])

  const value = useMemo(
    () => ({ sync, refresh, startSync }),
    [sync, refresh, startSync],
  )
  return <SyncContext.Provider value={value}>{children}</SyncContext.Provider>
}

export function useSync(): SyncCtx {
  const ctx = useContext(SyncContext)
  if (!ctx) throw new Error('useSync must be used within SyncProvider')
  return ctx
}

/** Reload page data once a Garmin sync finishes. */
export function useReloadWhenSyncFinishes(reload: () => void, enabled = true) {
  const { sync } = useSync()
  const running = !!sync?.is_running || sync?.status === 'running'
  const wasRunning = useRef(false)
  useEffect(() => {
    if (!enabled) return
    if (running) {
      wasRunning.current = true
      return
    }
    if (wasRunning.current) {
      wasRunning.current = false
      reload()
    }
  }, [running, enabled, reload])
}
