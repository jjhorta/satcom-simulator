// ── Auth ───────────────────────────────────────────────────────────────────────
export interface LoginRequest { username: string; password: string }
export interface TokenResponse {
  access_token: string
  token_type:   string
  user?:        UserInfo
}

// ── RBAC ──────────────────────────────────────────────────────────────────────
export type UserRole = 'admin' | 'team_manager' | 'creator' | 'viewer' | 'demo'

export interface UserInfo {
  id:                   number
  email:                string
  username:             string
  role:                 UserRole
  org_id?:              number | null
  org_name?:            string | null
  is_active?:           boolean
  created_at?:          string
  last_login_at?:       string
  jobs_used_this_month?: number
  demo_expires_at?:     string | null
  demo_jobs_remaining?: number | null
}

export interface OrgInfo {
  id:                number
  name:              string
  slug:              string
  owner_id:          number
  max_members:       number
  subscription_tier: string
  created_at?:       string
  members?:          UserInfo[]
}

export interface InvitationInfo {
  id:          number
  org_id:      number
  email:       string
  role:        UserRole
  token:       string
  expires_at:  string
  accepted_at: string | null
  created_at:  string
  link?:       string
}

export interface RegisterRequest {
  email:     string
  password:  string
  org_name?: string
  role?:     'creator' | 'demo'
}

// ── Options (from GET /api/options) ──────────────────────────────────────────
export interface ConstellationPreset {
  sats:                  number
  planes:                number
  altitude:              number
  inclination:           number
  phasing:               number
  sso:                   boolean
  description:           string
  default_comms?:        string
  default_satellite_type?: string
}

export interface ShellDef {
  sats:        number
  planes:      number
  inclination: number
  altitude_km: number
  phasing:     number
  name?:       string
}

export interface MultiShellPreset {
  shells:                  ShellDef[]
  description:             string
  default_comms?:          string
  default_satellite_type?: string
}

export interface MultiShellGroupEntry {
  shells:                  ShellDef[]
  description:             string
  builtin:                 boolean
  default_comms?:          string
  default_satellite_type?: string
}

export type MultiShellGroupRecord = Record<string, MultiShellGroupEntry>

export interface OptionsResponse {
  locations:              string[]
  comms_payloads:         string[]
  weather_scenarios:      string[]
  sea_routes:             string[]
  arctic_routes:          string[]
  platforms:              string[]
  backends:               string[]
  constellation_presets:  Record<string, ConstellationPreset>
  known_constellations:   Record<string, MultiShellPreset>
}

// ── Job models ─────────────────────────────────────────────────────────────────
export type JobMode = 'heatmap' | 'heatmap-rf' | 'sky' | 'orbit' | 'track' | 'route' | 'latency' | 'report'
export type JobStatusValue = 'queued' | 'running' | 'completed' | 'failed'

export interface JobFile {
  name:       string
  type:       string
  url:        string
  size_bytes: number
}

export interface JobStatus {
  job_id:       string
  mode:         JobMode
  status:       JobStatusValue
  created_at:   string
  started_at?:  string
  completed_at?: string
  error?:       string
  params:       Record<string, unknown>
  files:        JobFile[]
  log_tail?:    string
  title?:       string
  description?: string
  tags:         string[]
  user_id?:     number | null
  org_id?:      number | null
  username?:    string | null
}

export interface JobListItem {
  job_id:     string
  mode:       JobMode
  status:     JobStatusValue
  created_at: string
  title?:     string
  tags:       string[]
  user_id?:   number | null
  org_id?:    number | null
  username?:  string | null
}

// ── Request bodies ─────────────────────────────────────────────────────────────
// Base constellation geometry (mirrors ConstellationParams in models.py)
export interface ConstellationParams {
  sats:        number
  planes:      number
  altitude:    number
  phasing:     number
  inclination: number
  sso:         boolean
  backend:     'matplotlib' | 'plotly' | 'bokeh'
}

export interface HeatmapRequest extends ConstellationParams {
  comms:               string
  weather:             string
  res:                 number
  min_elev:            number
  bidi:                boolean
  constellation?:      string | null
  constellation_name?: string | null
  shells?:             ShellDef[] | null
  max_sats:            number
}

export interface HeatmapRfRequest extends ConstellationParams {
  comms:               string
  weather:             string
  res:                 number
  min_elev:            number
  bidi:                boolean
  constellation?:      string | null
  constellation_name?: string | null
  shells?:             ShellDef[] | null
  max_sats:            number
}

export interface SkyRequest extends ConstellationParams {
  location:            string
  coverage:            boolean
  comms:               string
  weather:             string
  bidi:                boolean
  duration:            number
  speed:               number
  trails:              boolean
  constellation?:      string | null
  constellation_name?: string | null
  shells?:             ShellDef[] | null
  max_sats:            number
}

export interface OrbitRequest extends ConstellationParams {
  comms:               string
  platform:            string
  trails:              boolean
  map:                 boolean
  beams:               boolean
  fill:                boolean
  min_elev:            number
  duration:            number
  constellation?:      string | null
  constellation_name?: string | null
  shells?:             ShellDef[] | null
  max_sats:            number
}

export interface TrackRequest extends ConstellationParams {
  duration: number
  map:      boolean
}

export interface RouteRequest extends ConstellationParams {
  route:               string
  comms:               string
  weather:             string
  bidi:                boolean
  duration:            number
  speed:               number
  min_elev:            number
  trails:              boolean
  constellation?:      string | null
  constellation_name?: string | null
  shells?:             ShellDef[] | null
  max_sats:            number
}

export interface LatencyRequest extends ConstellationParams {
  from_location:       string
  to_location:         string
  duration:            number
  step:                number
  isl_range:           number
  switching_delay:     number
  min_elev:            number
  no_fiber:            boolean
  constellation?:      string | null
  constellation_name?: string | null
  shells?:             ShellDef[] | null
  max_sats:            number
}

export type JobRequest =
  | { mode: 'heatmap';    params: HeatmapRequest }
  | { mode: 'heatmap-rf'; params: HeatmapRfRequest }
  | { mode: 'sky';        params: SkyRequest }
  | { mode: 'orbit';      params: OrbitRequest }
  | { mode: 'track';      params: TrackRequest }
  | { mode: 'route';      params: RouteRequest }
  | { mode: 'latency';    params: LatencyRequest }

// ── Full Report ────────────────────────────────────────────────────────────────
export interface ReportJobMap {
  heatmap:   string | null
  heatmapRf: string | null
  orbit:     string | null
  routes:    Record<string, string>   // routeName → jobId
}

export interface ReportState {
  reportId:       string
  label:          string            // constellation name or 'custom'
  title?:         string            // user-editable display name
  tags?:          string[]
  notes?:         string
  shareToken?:    string            // opaque token for public sharing
  createdAt:      string
  params:         Record<string, unknown>  // constellation params used for all sub-jobs
  selectedRoutes: string[]
  jobs:           ReportJobMap
  aiInsights?:    string
}

// ── Heatmap CSV row (from GET /api/jobs/:id/csv/:filename) ────────────────────
export interface HeatmapRow {
  latitude:         number
  longitude:        number
  availability_pct: number
  [key: string]:    number | string
}
