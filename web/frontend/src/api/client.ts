import axios from 'axios'
import type {
  LoginRequest,
  TokenResponse,
  OptionsResponse,
  JobStatus,
  JobListItem,
  JobRequest,
  HeatmapRow,
  MultiShellGroupRecord,
  ReportState,
  RegisterRequest,
  UserInfo,
  UserRole,
  OrgInfo,
  InvitationInfo,
} from '../types'
import { useAuthStore } from '../store/authStore'

// BASE_URL is injected by Vite from the `base` config option.
// In production: '/constellation-simulator/'  →  baseURL = '/constellation-simulator/api'
// In dev (same base):   '/constellation-simulator/'  → proxied by vite dev server
export const apiBase = `${import.meta.env.BASE_URL.replace(/\/$/, '')}/api`
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
      // Redirect to the app's base login path so hosted bases (e.g. /constellation-simulator/) work
      const base = import.meta.env.BASE_URL || '/'
      window.location.href = `${base}login`.replace(/([^:]?)\/\//g, '$1/')
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

export const register = (body: RegisterRequest) =>
  http.post<TokenResponse>('/auth/register', body).then((r) => r.data)

export const getMe = () =>
  http.get<UserInfo>('/auth/me').then((r) => r.data)

// ── Admin ──────────────────────────────────────────────────────────────────────
export const adminListUsers = (params?: { page?: number; per_page?: number; role?: string; org_id?: number; search?: string }) =>
  http.get<{ total: number; page: number; per_page: number; users: UserInfo[] }>('/admin/users', { params }).then((r) => r.data)

export const adminUpdateRole = (userId: number, newRole: UserRole) =>
  http.patch(`/admin/users/${userId}/role`, { new_role: newRole }).then((r) => r.data)

export const adminDeactivateUser = (userId: number) =>
  http.post(`/admin/users/${userId}/deactivate`).then((r) => r.data)

export const adminActivateUser = (userId: number) =>
  http.post(`/admin/users/${userId}/activate`).then((r) => r.data)

export const adminListOrgs = () =>
  http.get<OrgInfo[]>('/admin/organizations').then((r) => r.data)

// ── Org / Team ─────────────────────────────────────────────────────────────────
export const getTeamMembers = () =>
  http.get<{ members: UserInfo[] }>('/orgs/members').then((r) => r.data)

export const inviteTeamMember = (email: string, role: UserRole) =>
  http.post<{ invitation: InvitationInfo; link: string }>('/orgs/invite', { email, role }).then((r) => r.data)

export const acceptInvitation = (token: string) =>
  http.post<{ success: boolean; org_id: number; role: string }>(`/orgs/accept?token=${encodeURIComponent(token)}`).then((r) => r.data)

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

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const fetchTles = (jobId: string) =>
  http.get<any>(`/jobs/${jobId}/tles`).then((r) => r.data)

export const fetchAiAnalysis = (jobId: string): Promise<string | null> =>
  http.get<{ text: string }>(`/jobs/${jobId}/ai-analysis`)
    .then((r) => r.data.text)
    .catch(() => null)

export const saveAiAnalysis = (jobId: string, text: string): Promise<void> =>
  http.post(`/jobs/${jobId}/ai-analysis`, { text }).then(() => undefined)

// ── AI config (server-side key management) ────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const fetchAiConfig  = (): Promise<any> =>
  http.get('/ai/config').then((r) => r.data)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const updateAiConfig = (patch: any): Promise<any> =>
  http.put('/ai/config', patch).then((r) => r.data)

// ── Reports (server-side persistence) ────────────────────────────────────────
export const fetchReports = (): Promise<ReportState[]> =>
  http.get<ReportState[]>('/reports').then((r) => r.data)

export const saveReport = (report: ReportState): Promise<ReportState[]> =>
  http.post<ReportState[]>('/reports', report).then((r) => r.data)

export const deleteReport = (reportId: string): Promise<ReportState[]> =>
  http.delete<ReportState[]>(`/reports/${reportId}`).then((r) => r.data)

// Share a report — generates a public access token
export const shareReport = (reportId: string, password: string): Promise<{ token: string }> =>
  http.post<{ token: string }>(`/reports/${reportId}/share`, { password }).then((r) => r.data)

// Public (unauthenticated) — fetch a shared report using its token + password
export const fetchSharedReport = (token: string, password: string): Promise<ReportState> =>
  http.get<ReportState>(`/reports/shared/${token}`, { params: { password } }).then((r) => r.data)

// Share default password settings
export const getShareSettings  = (): Promise<{ has_default_password: boolean }> =>
  http.get<{ has_default_password: boolean }>('/reports/share-settings').then((r) => r.data)

export const updateShareSettings = (password: string): Promise<{ has_default_password: boolean }> =>
  http.put<{ has_default_password: boolean }>('/reports/share-settings', { password }).then((r) => r.data)

/** Construct a public URL for a file inside a shared report (no auth) */
export const sharedFileUrl = (token: string, jobId: string, filename: string, password: string) =>
  `${apiBase}/reports/shared/${encodeURIComponent(token)}/jobs/${jobId}/files/${encodeURIComponent(filename)}?password=${encodeURIComponent(password)}`

/** List files for a job in a shared report (no auth) */
export const fetchSharedJobFiles = (token: string, jobId: string, password: string): Promise<{ files: string[] }> =>
  http.get(`/reports/shared/${encodeURIComponent(token)}/jobs/${jobId}/files`, { params: { password } }).then((r) => r.data)

/** Fetch a CSV as JSON array for a job in a shared report (no auth) */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const fetchSharedCsv = (token: string, jobId: string, filename: string, password: string): Promise<any[]> =>
  http.get(`/reports/shared/${encodeURIComponent(token)}/jobs/${jobId}/csv/${encodeURIComponent(filename)}`, { params: { password } }).then((r) => r.data)

/** Fetch TCO data for a shared report (no auth) */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const fetchSharedTco = (token: string, jobId: string, password: string): Promise<any> =>
  http.get(`/reports/shared/${encodeURIComponent(token)}/jobs/${jobId}/tco`, { params: { password } }).then((r) => r.data)

/** Returns the base URL for the streaming AI proxy endpoint */
export const aiStreamUrl = (jobId: string) =>
  `${apiBase}/ai/jobs/${jobId}/stream`

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

// ── Multi-shell groups ──────────────────────────────────────────────────────────────
export const getMultiShellGroups = () =>
  http.get<MultiShellGroupRecord>('/settings/multi-shells').then((r) => r.data)
export const saveMultiShellGroup = (body: Record<string, unknown>) =>
  http.post<MultiShellGroupRecord>('/settings/multi-shells', body).then((r) => r.data)
export const updateMultiShellGroup = (name: string, body: Record<string, unknown>) =>
  http.put<MultiShellGroupRecord>(`/settings/multi-shells/${encodeURIComponent(name)}`, body).then((r) => r.data)
export const deleteMultiShellGroup = (name: string) =>
  http.delete<MultiShellGroupRecord>(`/settings/multi-shells/${encodeURIComponent(name)}`).then((r) => r.data)
export const resetMultiShellGroups = () =>
  http.delete<MultiShellGroupRecord>('/settings/multi-shells').then((r) => r.data)


// ── Billing API ──────────────────────────────────────────────────────────
export const getSubscription = () =>
  http.get('/billing/subscription').then((r) => r.data)

export const createCheckoutSession = (priceId: string) =>
  http.post<{ url: string }>('/billing/create-checkout', { price_id: priceId }).then((r) => r.data)

export const getPortalUrl = () =>
  http.get<{ url: string }>('/billing/portal').then((r) => r.data)

// ── Batch Sweep API ──────────────────────────────────────────────────────────
export const submitBatchJob = (body: Record<string, unknown>) =>
  http.post('/jobs/batch', body).then((r) => r.data)
// ── CARL API ────────────────────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const getCarlConfig = (): Promise<any> =>
  http.get('/carl/config').then((r) => r.data)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const updateCarlConfig = (body: Record<string, unknown>): Promise<any> =>
  http.put('/carl/config', body).then((r) => r.data)
// ── CARL Chat API ──────────────────────────────────────────────────────
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const listCarlChats = (): Promise<any> =>
  http.get('/carl/chats').then((r) => r.data)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const createCarlChat = (name?: string): Promise<any> =>
  http.post('/carl/chats', { name }).then((r) => r.data)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const getCarlChat = (chatId: string): Promise<any> =>
  http.get(`/carl/chats/${chatId}`).then((r) => r.data)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const updateCarlChat = (chatId: string, name: string): Promise<any> =>
  http.put(`/carl/chats/${chatId}`, { name }).then((r) => r.data)

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const deleteCarlChat = (chatId: string): Promise<any> =>
  http.delete(`/carl/chats/${chatId}`).then((r) => r.data)

// ── Password reset ───────────────────────────────────────────────────-
export const forgotPassword = (email: string) =>
  http.post('/auth/forgot-password', { email }).then(r => r.data)

export const resetPassword = (token: string, password: string) =>
  http.post('/auth/reset-password', { token, password }).then(r => r.data)
