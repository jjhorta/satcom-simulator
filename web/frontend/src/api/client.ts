import axios from 'axios'
import type {
  LoginRequest,
  TokenResponse,
  OptionsResponse,
  JobStatus,
  JobListItem,
  JobRequest,
  HeatmapRow,
} from '../types'
import { useAuthStore } from '../store/authStore'

// BASE_URL is injected by Vite from the `base` config option.
// In production: '/constellation-simulator/'  →  baseURL = '/constellation-simulator/api'
// In dev (same base):   '/constellation-simulator/'  → proxied by vite dev server
const apiBase = `${import.meta.env.BASE_URL.replace(/\/$/, '')}/api`
const http = axios.create({ baseURL: apiBase })

// Attach JWT bearer token to every request
http.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// On 401 — clear token and reload to force login
http.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  },
)

// ── Auth ──────────────────────────────────────────────────────────────────────
// FastAPI OAuth2PasswordRequestForm expects form-urlencoded, not JSON.
export const login = (body: LoginRequest) => {
  const form = new URLSearchParams()
  form.append('username', body.username)
  form.append('password', body.password)
  return http
    .post<TokenResponse>('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
    .then((r) => r.data)
}

// ── Options ───────────────────────────────────────────────────────────────────
export const fetchOptions = () =>
  http.get<OptionsResponse>('/options').then((r) => r.data)

// ── Jobs ──────────────────────────────────────────────────────────────────────
export const listJobs = () =>
  http.get<JobListItem[]>('/jobs').then((r) => r.data)

export const getJob = (jobId: string) =>
  http.get<JobStatus>(`/jobs/${jobId}`).then((r) => r.data)

export const submitJob = (body: JobRequest) =>
  http.post<{ job_id: string; status: string }>('/jobs', body).then((r) => r.data)

export const deleteJob = (jobId: string) =>
  http.delete(`/jobs/${jobId}`).then((r) => r.data)

export const updateJobMeta = (jobId: string, body: { title?: string; description?: string; tags?: string[] }) =>
  http.patch<JobStatus>(`/jobs/${jobId}`, body).then((r) => r.data)

// ── Results ───────────────────────────────────────────────────────────────────
export const fetchCsv = (jobId: string, filename: string) =>
  http.get<HeatmapRow[]>(`/jobs/${jobId}/csv/${filename}`).then((r) => r.data)

/** Returns a fully-qualified URL for a job file (image, html, txt, etc.) */
export const fileUrl = (jobId: string, filename: string) =>
  `${apiBase}/jobs/${jobId}/files/${filename}`

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const fetchTco = (jobId: string) =>
  http.get<any>(`/jobs/${jobId}/tco`).then((r) => r.data)

export const fetchAiAnalysis = (jobId: string): Promise<string | null> =>
  http.get<{ text: string }>(`/jobs/${jobId}/ai-analysis`)
    .then((r) => r.data.text)
    .catch(() => null)

export const saveAiAnalysis = (jobId: string, text: string): Promise<void> =>
  http.post(`/jobs/${jobId}/ai-analysis`, { text }).then(() => undefined)

// ── Simulation physics settings ───────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const getSimSettings  = () => http.get<any>('/settings').then((r) => r.data)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const updateSimSettings = (body: any) => http.put<any>('/settings', body).then((r) => r.data)
export const resetCommsTech  = (tech: string) => http.delete(`/settings/comms/${tech}`).then((r) => r.data)
export const resetWeather    = () => http.delete('/settings/weather').then((r) => r.data)

// ── Route settings ────────────────────────────────────────────────────────────
export const getRoutes       = () => http.get<any>('/settings/routes').then((r) => r.data)
export const updateRoute     = (category: string, name: string, waypoints: [string, number, number][]) =>
  http.put<any>(`/settings/routes/${category}/${name}`, waypoints).then((r) => r.data)
export const resetRoute      = (category: string, name: string) =>
  http.delete<any>(`/settings/routes/${category}/${name}`).then((r) => r.data)

// ── TCO settings ──────────────────────────────────────────────────────────────
export const getTcoSettings   = () => http.get<any>('/settings/tco').then((r) => r.data)
export const resetTcoSettings = () => http.delete<any>('/settings/tco').then((r) => r.data)

// ── Constellation presets ─────────────────────────────────────────────────────
export const getConstellationPresets = () => http.get<any>('/settings/constellations').then((r) => r.data)
export const saveConstellationPreset = (body: Record<string, unknown>) =>
  http.post<any>('/settings/constellations', body).then((r) => r.data)
export const deleteConstellationPreset = (name: string) =>
  http.delete<any>(`/settings/constellations/${encodeURIComponent(name)}`).then((r) => r.data)
export const resetConstellationPresets = () =>
  http.delete<any>('/settings/constellations').then((r) => r.data)
