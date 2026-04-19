// ── Auth ───────────────────────────────────────────────────────────────────────
export interface LoginRequest { username: string; password: string }
export interface TokenResponse { access_token: string; token_type: string }

// ── Options (from GET /api/options) ──────────────────────────────────────────
export interface ConstellationPreset {
  sats:        number
  planes:      number
  altitude:    number
  inclination: number
  phasing:     number
  sso:         boolean
  description: string
}

export interface OptionsResponse {
  locations:              string[]
  comms_payloads:         string[]
  weather_scenarios:      string[]
  sea_routes:             string[]
  arctic_routes:          string[]
  platforms:              string[]
  backends:               string[]
  constellation_presets:  Record<string, ConstellationPreset>
}

// ── Job models ─────────────────────────────────────────────────────────────────
export type JobMode = 'heatmap' | 'sky' | 'orbit' | 'track' | 'route'
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
}

export interface JobListItem {
  job_id:     string
  mode:       JobMode
  status:     JobStatusValue
  created_at: string
  title?:     string
  tags:       string[]
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
  comms:     string
  weather:   string
  res:       number
  min_elev:  number
  bidi:      boolean
}

export interface SkyRequest extends ConstellationParams {
  location:  string
  coverage:  boolean
  comms:     string
  weather:   string
  bidi:      boolean
  duration:  number
  speed:     number
  trails:    boolean
}

export interface OrbitRequest extends ConstellationParams {
  comms:    string
  platform: string
  trails:   boolean
  map:      boolean
  beams:    boolean
  min_elev: number
  duration: number
}

export interface TrackRequest extends ConstellationParams {
  duration: number
  map:      boolean
}

export interface RouteRequest extends ConstellationParams {
  route:    string
  comms:    string
  weather:  string
  bidi:     boolean
  duration: number
  speed:    number
  min_elev: number
  trails:   boolean
}

export type JobRequest =
  | { mode: 'heatmap'; params: HeatmapRequest }
  | { mode: 'sky';     params: SkyRequest }
  | { mode: 'orbit';   params: OrbitRequest }
  | { mode: 'track';   params: TrackRequest }
  | { mode: 'route';   params: RouteRequest }

// ── Heatmap CSV row (from GET /api/jobs/:id/csv/:filename) ────────────────────
export interface HeatmapRow {
  latitude:         number
  longitude:        number
  availability_pct: number
  [key: string]:    number | string
}
