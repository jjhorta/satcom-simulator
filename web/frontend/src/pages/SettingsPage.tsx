import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { ArrowLeft, Satellite, RotateCcw, Save, ChevronDown, ChevronRight, Plus, Trash2, Sparkles, Brain, ShieldCheck, Pencil, Check, X as XIcon, Share2, Lock, Bot } from 'lucide-react'
import { useAiStore, isAiConfigured } from '../store/aiStore'
import { getSimSettings, updateSimSettings, resetCommsTech, resetWeather, getRoutes, updateRoute, resetRoute, getTcoSettings, resetTcoSettings, getConstellationPresets, saveConstellationPreset, deleteConstellationPreset, resetConstellationPresets, getMultiShellGroups, saveMultiShellGroup, updateMultiShellGroup, deleteMultiShellGroup, resetMultiShellGroups, fetchAiConfig, updateAiConfig, getShareSettings, updateShareSettings, getCarlConfig, updateCarlConfig } from '../api/client'
import type { ConstellationPreset, ShellDef, MultiShellGroupRecord } from '../types'
import 'leaflet/dist/leaflet.css'
import { MapContainer, TileLayer, Polyline, useMap } from 'react-leaflet'
import type { LatLngBoundsExpression } from 'leaflet'

// ── Types ─────────────────────────────────────────────────────────────────────

interface CommsPayload {
  desc?: string; mod?: string
  bw: number
  dl_freq: number; sat_p_tx: number; sat_g_tx: number
  gnd_g_rx: number; gnd_nf: number; req_snr_dl: number
  ul_freq: number; gnd_p_tx: number; gnd_g_tx: number
  sat_g_rx: number; sat_nf: number; req_snr_ul: number
}

interface SimSettings {
  comms_payloads:    Record<string, CommsPayload>
  weather_scenarios: Record<string, number>
}

type Waypoint = [string, number, number]   // [name, lat, lon]
interface RouteSettings {
  sea_routes:    Record<string, Waypoint[]>
  arctic_routes: Record<string, Waypoint[]>
}

interface TcoPlatform  { typical_mass_kg: number; unit_cost: number; description?: string }
interface TcoLaunchVehicle {
  base_cost?: number; cost_per_kg?: number
  cost_per_launch?: number
  max_payload_kg: number; typical_batch_size: number; description?: string
}
interface TcoConfig {
  satellite_platforms: Record<string, TcoPlatform>
  payload_multipliers: Record<string, number>
  launch_vehicles:     Record<string, TcoLaunchVehicle>
  development:         { initial_rd: number; payload_development: number; ground_segment: number }
  operations: {
    ground_stations:     { stations_needed_per_100_sats: number; initial_capex: number; annual_opex: number }
    mission_control:     { initial_capex: number; annual_opex: number }
    network_operations:  { cost_per_sat_per_year: number }
    staff:               { engineers_per_100_sats: number; annual_cost_per_engineer: number }
  }
  insurance:           { launch_insurance_pct: number; annual_in_orbit_pct: number }
  decommissioning:     { cost_per_satellite: number; regulatory_compliance: number }
  deployment:          Record<string, { planes_per_launch: number; propulsion_cost_per_sat: number; deployment_opex_factor: number }>
}

// ── Field metadata ─────────────────────────────────────────────────────────────

const COMMS_FIELDS: { key: keyof CommsPayload; label: string; unit: string; section: 'dl' | 'ul' | 'shared' }[] = [
  { key: 'bw',         label: 'Bandwidth',           unit: 'Hz',  section: 'shared' },
  { key: 'dl_freq',    label: 'DL Frequency',         unit: 'MHz', section: 'dl' },
  { key: 'sat_p_tx',   label: 'Sat Tx Power',         unit: 'W',   section: 'dl' },
  { key: 'sat_g_tx',   label: 'Sat Tx Antenna Gain',  unit: 'dBi', section: 'dl' },
  { key: 'gnd_g_rx',   label: 'Ground Rx Gain',       unit: 'dBi', section: 'dl' },
  { key: 'gnd_nf',     label: 'Ground Noise Figure',  unit: 'dB',  section: 'dl' },
  { key: 'req_snr_dl', label: 'Required SNR (DL)',    unit: 'dB',  section: 'dl' },
  { key: 'ul_freq',    label: 'UL Frequency',         unit: 'MHz', section: 'ul' },
  { key: 'gnd_p_tx',   label: 'Ground Tx Power',      unit: 'W',   section: 'ul' },
  { key: 'gnd_g_tx',   label: 'Ground Tx Gain',       unit: 'dBi', section: 'ul' },
  { key: 'sat_g_rx',   label: 'Sat Rx Gain',          unit: 'dBi', section: 'ul' },
  { key: 'sat_nf',     label: 'Sat Noise Figure',     unit: 'dB',  section: 'ul' },
  { key: 'req_snr_ul', label: 'Required SNR (UL)',    unit: 'dB',  section: 'ul' },
]

const WEATHER_LABELS: Record<string, string> = {
  clear:    'Clear sky',
  smoke:    'Smoke / haze',
  drizzle:  'Drizzle',
  rain:     'Rain',
  storm:    'Storm',
  tropical: 'Tropical downpour',
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const inputCls =
  'w-full px-2 py-1 rounded bg-gray-800 border border-gray-700 text-xs text-white ' +
  'focus:outline-none focus:border-indigo-500 text-right tabular-nums'

function NumInput({
  value, onChange,
}: { value: number; onChange: (v: number) => void }) {
  return (
    <input
      type="number"
      step="any"
      className={inputCls}
      value={value}
      onChange={(e) => {
        const n = parseFloat(e.target.value)
        if (!isNaN(n)) onChange(n)
      }}
    />
  )
}

// ── Comms tech accordion ──────────────────────────────────────────────────────

function CommsCard({
  tech, payload, onSave, onReset,
}: {
  tech: string
  payload: CommsPayload
  onSave: (tech: string, updated: CommsPayload) => void
  onReset: (tech: string) => void
}) {
  const [open,  setOpen]  = useState(false)
  const [draft, setDraft] = useState<CommsPayload>({ ...payload })

  const setField = (key: keyof CommsPayload, val: number) =>
    setDraft((d) => ({ ...d, [key]: val }))

  const sections = (['shared', 'dl', 'ul'] as const).map((s) => ({
    label: s === 'shared' ? 'General' : s === 'dl' ? 'Downlink (Sat → Ground)' : 'Uplink (Ground → Sat)',
    fields: COMMS_FIELDS.filter((f) => f.section === s),
  }))

  return (
    <div className="border border-gray-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-900 hover:bg-gray-800 transition-colors"
      >
        <div className="flex items-center gap-3">
          {open ? <ChevronDown className="w-4 h-4 text-gray-500" /> : <ChevronRight className="w-4 h-4 text-gray-500" />}
          <span className="text-sm font-mono font-semibold text-indigo-300">{tech.toUpperCase()}</span>
          {payload.desc && <span className="text-xs text-gray-500">{payload.desc}</span>}
        </div>
        {payload.mod && (
          <span className="text-xs text-gray-600 font-mono">{payload.mod}</span>
        )}
      </button>

      {open && (
        <div className="px-4 pb-4 pt-2 bg-gray-950 space-y-4">
          {sections.map(({ label, fields }) => (
            <div key={label}>
              <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">{label}</p>
              <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
                {fields.map(({ key, label: flabel, unit }) => (
                  <div key={key} className="flex items-center gap-2">
                    <span className="text-xs text-gray-400 flex-1 truncate">
                      {flabel}
                      <span className="ml-1 text-gray-600">({unit})</span>
                    </span>
                    <div className="w-24 flex-shrink-0">
                      <NumInput
                        value={draft[key] as number}
                        onChange={(v) => setField(key, v)}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}

          <div className="flex gap-2 pt-2 border-t border-gray-800">
            <button
              onClick={() => onSave(tech, draft)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                         bg-indigo-600 text-white hover:bg-indigo-500 transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              Save changes
            </button>
            <button
              onClick={() => { onReset(tech); setOpen(false) }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                         text-gray-400 bg-gray-800 hover:text-white hover:bg-gray-700 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset to defaults
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── TCO helpers ───────────────────────────────────────────────────────────────

const M = '$M'  // currency unit label
const PCT = '%' // percent label

function TcoSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-4">{title}</p>
      {children}
    </div>
  )
}

function TcoRow({ label, unit, value, onChange }: { label: string; unit: string; value: number; onChange: (v: number) => void }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-300 flex-1 truncate">{label}</span>
      <div className="w-28 flex-shrink-0">
        <NumInput value={value} onChange={onChange} />
      </div>
      <span className="text-xs text-gray-600 w-8">{unit}</span>
    </div>
  )
}

// ── Route map preview ─────────────────────────────────────────────────────────

function FitRouteBounds({ waypoints }: { waypoints: Waypoint[] }) {
  const map = useMap()
  if (waypoints.length >= 2) {
    const lats = waypoints.map((w) => w[1])
    const lons = waypoints.map((w) => w[2])
    const bounds: LatLngBoundsExpression = [
      [Math.min(...lats) - 2, Math.min(...lons) - 2],
      [Math.max(...lats) + 2, Math.max(...lons) + 2],
    ]
    map.fitBounds(bounds, { animate: false })
  }
  return null
}

// ── Route accordion card ──────────────────────────────────────────────────────

function RouteCard({
  category, name, waypoints, onSave, onReset,
}: {
  category: string
  name: string
  waypoints: Waypoint[]
  onSave: (category: string, name: string, wps: Waypoint[]) => void
  onReset: (category: string, name: string) => void
}) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<Waypoint[]>(waypoints.map((w) => [...w] as Waypoint))

  const updateWp = (idx: number, field: 0 | 1 | 2, val: string | number) => {
    setDraft((d) => {
      const copy = d.map((w) => [...w] as Waypoint)
      ;(copy[idx] as unknown as (string | number)[])[field] = val
      return copy
    })
  }

  const addWp = () =>
    setDraft((d) => [...d, ['new_wp', 0, 0] as Waypoint])

  const removeWp = (idx: number) =>
    setDraft((d) => d.filter((_, i) => i !== idx))

  const positions = draft.filter((w) => !isNaN(w[1]) && !isNaN(w[2])).map((w) => [w[1], w[2]] as [number, number])

  return (
    <div className="border border-gray-800 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-900 hover:bg-gray-800 transition-colors"
      >
        <div className="flex items-center gap-3">
          {open ? <ChevronDown className="w-4 h-4 text-gray-500" /> : <ChevronRight className="w-4 h-4 text-gray-500" />}
          <span className="text-sm font-mono font-semibold text-indigo-300">{name}</span>
          <span className="text-xs text-gray-500">{waypoints.length} waypoints</span>
        </div>
        <span className="text-xs text-gray-600 font-mono">{category === 'sea_routes' ? 'Sea' : 'Arctic'}</span>
      </button>

      {open && (
        <div className="px-4 pb-4 pt-2 bg-gray-950 space-y-4">
          {/* Mini map preview */}
          {positions.length >= 2 && (
            <div className="rounded overflow-hidden border border-gray-800" style={{ height: 180 }}>
              <MapContainer
                center={positions[0]}
                zoom={3}
                style={{ width: '100%', height: '100%' }}
                zoomControl={false}
                attributionControl={false}
              >
                <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" />
                <Polyline positions={positions} pathOptions={{ color: '#6366f1', weight: 2, dashArray: '4 4' }} />
                <FitRouteBounds waypoints={draft} />
              </MapContainer>
            </div>
          )}

          {/* Waypoint table */}
          <div className="space-y-1">
            <div className="grid grid-cols-[auto_1fr_1fr_1fr_auto] gap-2 text-xs text-gray-500 font-medium px-1">
              <span>#</span><span>Name</span><span>Latitude</span><span>Longitude</span><span />
            </div>
            {draft.map((wp, idx) => (
              <div key={idx} className="grid grid-cols-[auto_1fr_1fr_1fr_auto] gap-2 items-center">
                <span className="text-xs text-gray-600 tabular-nums w-5 text-right">{idx + 1}</span>
                <input
                  type="text"
                  value={wp[0]}
                  onChange={(e) => updateWp(idx, 0, e.target.value)}
                  className={inputCls}
                  placeholder="name"
                />
                <input
                  type="number"
                  step="0.0001"
                  value={wp[1]}
                  onChange={(e) => updateWp(idx, 1, parseFloat(e.target.value) || 0)}
                  className={inputCls}
                />
                <input
                  type="number"
                  step="0.0001"
                  value={wp[2]}
                  onChange={(e) => updateWp(idx, 2, parseFloat(e.target.value) || 0)}
                  className={inputCls}
                />
                <button
                  onClick={() => removeWp(idx)}
                  className="text-gray-600 hover:text-red-400 transition-colors"
                  title="Remove waypoint"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>

          <button
            onClick={addWp}
            className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
            Add waypoint
          </button>

          <div className="flex gap-2 pt-2 border-t border-gray-800">
            <button
              onClick={() => onSave(category, name, draft)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                         bg-indigo-600 text-white hover:bg-indigo-500 transition-colors"
            >
              <Save className="w-3.5 h-3.5" />
              Save changes
            </button>
            <button
              onClick={() => { onReset(category, name); setOpen(false) }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                         text-gray-400 bg-gray-800 hover:text-white hover:bg-gray-700 transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset to defaults
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const qc = useQueryClient()
  const [activeTab, setActiveTab] = useState<'comms' | 'weather' | 'routes' | 'tco' | 'constellations' | 'ai'>('comms')
  const aiStatus = useAiStore()
  const aiOk     = isAiConfigured(aiStatus)

  // Load AI config status from backend on mount
  useEffect(() => {
    fetchAiConfig().then((cfg) => {
      aiStatus.setStatus({
        keyIsSet:     cfg.key_is_set,
        maskedKey:    cfg.masked_key,
        model:        cfg.model,
        baseUrl:      cfg.base_url,
        systemPrompt: cfg.system_prompt,
      })
    }).catch(() => {})
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Local draft state for the AI settings form
  const [aiDraft, setAiDraft] = useState({
    api_key:       '',   // write-only: empty = keep existing
    base_url:      '',
    model:         '',
    system_prompt: '',
  })
  const [aiSaving, setAiSaving] = useState(false)
  const [aiSaved,  setAiSaved]  = useState(false)

  // ── Share password state ───────────────────────────────────────────────────
  const [shareHasDefault,  setShareHasDefault]  = useState(false)
  const [sharePwd,         setSharePwd]         = useState('')
  const [shareSaving,      setShareSaving]       = useState(false)
  const [shareSaved,       setShareSaved]        = useState(false)
  const [shareError,       setShareError]        = useState('')

  useEffect(() => {
    if (activeTab === 'ai') {
      getShareSettings().then((s) => setShareHasDefault(s.has_default_password)).catch(() => {})
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab])

  const saveSharePassword = async () => {
    const pwd = sharePwd.trim()
    if (pwd && pwd.length < 4) { setShareError('Password must be at least 4 characters.'); return }
    setShareSaving(true); setShareError('')
    try {
      const result = await updateShareSettings(pwd)
      setShareHasDefault(result.has_default_password)
      setSharePwd('')
      setShareSaved(true)
      setTimeout(() => setShareSaved(false), 2000)
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? (e as Error)?.message ?? 'Failed to save.'
      setShareError(msg)
    } finally {
      setShareSaving(false)
    }
  }

  // Sync draft from store when tab opens
  useEffect(() => {
    if (activeTab === 'ai') {
      setAiDraft((d) => ({
        ...d,
        base_url:      aiStatus.baseUrl,
        model:         aiStatus.model,
        system_prompt: aiStatus.systemPrompt,
      }))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab])

  const saveAiSettings = async () => {
    setAiSaving(true)
    try {
      const cfg = await updateAiConfig(aiDraft)
      aiStatus.setStatus({
        keyIsSet:     cfg.key_is_set,
        maskedKey:    cfg.masked_key,
        model:        cfg.model,
        baseUrl:      cfg.base_url,
        systemPrompt: cfg.system_prompt,
      })
      setAiDraft((d) => ({ ...d, api_key: '' }))  // clear key field after save
      setAiSaved(true)
      setTimeout(() => setAiSaved(false), 2500)
    } finally {
      setAiSaving(false)
    }
  }
  const [weatherDraft, setWeatherDraft] = useState<Record<string, number> | null>(null)
  const [saving, setSaving] = useState(false)

  const { data: settings, isLoading, isError } = useQuery<SimSettings>({
    queryKey: ['sim-settings'],
    queryFn: getSimSettings,
  })

  const { data: routeSettings, isLoading: routesLoading, isError: routesError } = useQuery<RouteSettings>({
    queryKey: ['route-settings'],
    queryFn: getRoutes,
  })

  const { data: tcoSettings, isLoading: tcoLoading, isError: tcoError } = useQuery<TcoConfig>({
    queryKey: ['tco-settings'],
    queryFn: getTcoSettings,
  })

  const [tcoDraft, setTcoDraft] = useState<TcoConfig | null>(null)
  const tco = tcoDraft ?? tcoSettings ?? null

  const { data: constellationPresets, isLoading: consLoading, isError: consError } = useQuery<Record<string, ConstellationPreset>>({
    queryKey: ['constellation-presets'],
    queryFn: getConstellationPresets,
  })

  const { data: multiShellGroups, isLoading: msLoading } = useQuery<MultiShellGroupRecord>({
    queryKey: ['multi-shell-groups'],
    queryFn: getMultiShellGroups,
  })

  // New multi-shell form state
  type ShellDraft = ShellDef & { _key: number }
  const emptyShell = (): ShellDraft => ({ _key: Date.now(), sats: 12, planes: 3, inclination: 53, altitude_km: 600, phasing: 1, name: '' })
  const [msName, setMsName] = useState('')
  const [msDesc, setMsDesc] = useState('')
  const [msShells, setMsShells] = useState<ShellDraft[]>([emptyShell()])
  const addMsShell = () => setMsShells((s) => [...s, emptyShell()])
  const removeMsShell = (key: number) => setMsShells((s) => s.filter((sh) => sh._key !== key))
  const updateMsShell = (key: number, field: keyof ShellDef, val: string | number) =>
    setMsShells((s) => s.map((sh) => sh._key === key ? { ...sh, [field]: val } : sh))

  // New constellation form state
  const emptyPreset: ConstellationPreset & { name: string } = {
    name: '', sats: 12, planes: 3, altitude: 600, inclination: 53.0, phasing: 1, sso: false, description: '', default_comms: '', default_satellite_type: '',
  }
  const [newPreset, setNewPreset] = useState(emptyPreset)
  const [editingName, setEditingName] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<(ConstellationPreset & { name: string }) | null>(null)
  const commsList = Object.keys(settings?.comms_payloads ?? {})
  const platformsList = tcoSettings ? Object.keys(tcoSettings.satellite_platforms) : ['nanosat', 'microsat', 'smallsat', 'mediumsat', 'largesat']
  const [msDefaultComms, setMsDefaultComms] = useState('')
  const [msDefaultSatType, setMsDefaultSatType] = useState('')
  const [msEditingName, setMsEditingName] = useState<string | null>(null)

  const startEditMultiShell = (name: string, g: { shells: ShellDef[]; description: string; default_comms?: string; default_satellite_type?: string }) => {
    setMsEditingName(name)
    setMsName(name)
    setMsDesc(g.description || '')
    setMsDefaultComms(g.default_comms || '')
    setMsDefaultSatType(g.default_satellite_type || '')
    setMsShells(g.shells.map((s, i) => ({ ...s, _key: Date.now() + i })))
    // Scroll the form into view
    setTimeout(() => {
      const el = document.getElementById('multi-shell-form')
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }, 50)
  }

  const cancelEditMultiShell = () => {
    setMsEditingName(null)
    setMsName('')
    setMsDesc('')
    setMsShells([emptyShell()])
    setMsDefaultComms('')
    setMsDefaultSatType('')
  }

  const mutateSave = useMutation({
    mutationFn: updateSimSettings,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sim-settings'] }),
  })

  const mutateResetTech = useMutation({
    mutationFn: resetCommsTech,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['sim-settings'] }),
  })

  const mutateResetWeather = useMutation({
    mutationFn: resetWeather,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['sim-settings'] })
      setWeatherDraft(null)
    },
  })

  const mutateSaveRoute = useMutation({
    mutationFn: ({ category, name, waypoints }: { category: string; name: string; waypoints: Waypoint[] }) =>
      updateRoute(category, name, waypoints),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['route-settings'] }),
  })

  const mutateResetRoute = useMutation({
    mutationFn: ({ category, name }: { category: string; name: string }) => resetRoute(category, name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['route-settings'] }),
  })

  const mutateResetTco = useMutation({
    mutationFn: resetTcoSettings,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tco-settings'] })
      setTcoDraft(null)
    },
  })

  const mutateSaveConstellation = useMutation({
    mutationFn: saveConstellationPreset,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['constellation-presets'] })
      qc.invalidateQueries({ queryKey: ['options'] })
      setNewPreset(emptyPreset)
      setEditingName(null)
      setEditDraft(null)
    },
  })

  const mutateDeleteConstellation = useMutation({
    mutationFn: deleteConstellationPreset,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['constellation-presets'] })
      qc.invalidateQueries({ queryKey: ['options'] })
    },
  })

  const mutateResetConstellations = useMutation({
    mutationFn: resetConstellationPresets,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['constellation-presets'] })
      qc.invalidateQueries({ queryKey: ['options'] })
    },
  })

  const mutateSaveMultiShell = useMutation({
    mutationFn: saveMultiShellGroup,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['multi-shell-groups'] })
      qc.invalidateQueries({ queryKey: ['options'] })
      setMsName('')
      setMsDesc('')
      setMsShells([emptyShell()])
      setMsDefaultComms('')
      setMsDefaultSatType('')
    },
  })

  const mutateUpdateMultiShell = useMutation({
    mutationFn: ({ name, body }: { name: string; body: Record<string, unknown> }) => updateMultiShellGroup(name, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['multi-shell-groups'] })
      qc.invalidateQueries({ queryKey: ['options'] })
      cancelEditMultiShell()
    },
  })

  const mutateDeleteMultiShell = useMutation({
    mutationFn: deleteMultiShellGroup,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['multi-shell-groups'] })
      qc.invalidateQueries({ queryKey: ['options'] })
    },
  })

  const mutateResetMultiShell = useMutation({
    mutationFn: resetMultiShellGroups,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['multi-shell-groups'] })
      qc.invalidateQueries({ queryKey: ['options'] })
    },
  })

  const handleSaveComms = async (tech: string, updated: CommsPayload) => {
    await mutateSave.mutateAsync({ comms_payloads: { [tech]: updated } })
  }

  const handleSaveWeather = async () => {
    if (!weatherDraft) return
    setSaving(true)
    await mutateSave.mutateAsync({ weather_scenarios: weatherDraft })
    setWeatherDraft(null)
    setSaving(false)
  }

  const handleSaveRoute = async (category: string, name: string, wps: Waypoint[]) => {
    await mutateSaveRoute.mutateAsync({ category, name, waypoints: wps })
  }

  const handleResetRoute = async (category: string, name: string) => {
    await mutateResetRoute.mutateAsync({ category, name })
  }

  const handleSaveTco = async () => {
    if (!tco) return
    await mutateSave.mutateAsync({ tco_config: tco })
    qc.invalidateQueries({ queryKey: ['tco-settings'] })
    setTcoDraft(null)
  }

  const weatherValues = weatherDraft ?? settings?.weather_scenarios ?? {}

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top bar */}
      <header className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <Satellite className="w-5 h-5 text-indigo-400" />
          <span className="font-semibold text-white">Constellation Simulator</span>
          <span className="text-gray-600 mx-1">/</span>
          <span className="text-sm text-gray-400">Physics Settings</span>
        </div>
        <Link
          to="/"
          className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to simulations
        </Link>
      </header>

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-8">
          <div className="mb-6">
            <h1 className="text-lg font-bold text-white">Simulation Physics Settings</h1>
            <p className="text-sm text-gray-500 mt-1">
              Override link budget parameters and atmospheric attenuation. Changes apply to
              all future simulations. The original Python defaults are never modified.
            </p>
          </div>

          {/* Tab bar */}
          <div className="flex gap-1 mb-6 border-b border-gray-800">
            {(['comms', 'weather', 'routes', 'tco', 'constellations', 'ai'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                  activeTab === tab
                    ? 'text-white border-indigo-500'
                    : 'text-gray-500 border-transparent hover:text-gray-300'
                }`}
              >
                {tab === 'comms' ? 'Communications Link Budget'
                  : tab === 'weather' ? 'Weather Attenuation'
                  : tab === 'routes' ? 'Routes'
                  : tab === 'tco' ? 'Business Model (TCO)'
                  : tab === 'constellations' ? 'Constellations'
                  : 'AI Assistant'}
              </button>
            ))}
          </div>

          {isLoading && <p className="text-sm text-gray-500 animate-pulse">Loading settings…</p>}
          {isError  && <p className="text-sm text-red-400">Failed to load settings.</p>}

          {/* ── Comms tab ── */}
          {settings && activeTab === 'comms' && (
            <div className="space-y-3">
              <p className="text-xs text-gray-500">
                Each technology's link budget is used to compute whether a satellite–ground
                contact has sufficient SNR margin. Expand a technology to edit its parameters.
              </p>
              {Object.entries(settings.comms_payloads).map(([tech, payload]) => (
                <CommsCard
                  key={tech}
                  tech={tech}
                  payload={payload}
                  onSave={handleSaveComms}
                  onReset={(t) => mutateResetTech.mutateAsync(t)}
                />
              ))}
            </div>
          )}

          {/* ── Weather tab ── */}
          {settings && activeTab === 'weather' && (
            <div className="space-y-4">
              <p className="text-xs text-gray-500">
                Rain/weather attenuation added to the link budget in dB. Higher values mean
                more signal loss, reducing effective coverage. 0 dB = no extra attenuation.
              </p>
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
                {Object.entries(settings.weather_scenarios).map(([key, def]) => (
                  <div key={key} className="flex items-center gap-4">
                    <span className="text-sm text-gray-300 w-40 flex-shrink-0">
                      {WEATHER_LABELS[key] ?? key}
                    </span>
                    <div className="w-28">
                      <NumInput
                        value={weatherValues[key] ?? def}
                        onChange={(v) =>
                          setWeatherDraft((d) => ({
                            ...(d ?? settings.weather_scenarios),
                            [key]: v,
                          }))
                        }
                      />
                    </div>
                    <span className="text-xs text-gray-600">dB</span>
                  </div>
                ))}
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleSaveWeather}
                  disabled={!weatherDraft || saving}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                             bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors"
                >
                  <Save className="w-3.5 h-3.5" />
                  {saving ? 'Saving…' : 'Save weather settings'}
                </button>
                <button
                  onClick={() => mutateResetWeather.mutateAsync()}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                             text-gray-400 bg-gray-800 hover:text-white hover:bg-gray-700 transition-colors"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Reset to defaults
                </button>
              </div>
            </div>
          )}

          {/* ── Routes tab ── */}
          {activeTab === 'routes' && (
            <div className="space-y-6">
              <p className="text-xs text-gray-500">
                Edit the waypoints of each sea or arctic route. Changes affect which paths
                are evaluated in future simulations. Use "Reset to defaults" to restore
                the original Python-defined waypoints.
              </p>
              {routesLoading && <p className="text-sm text-gray-500 animate-pulse">Loading routes…</p>}
              {routesError  && <p className="text-sm text-red-400">Failed to load routes.</p>}
              {routeSettings && (
                <>
                  <div>
                    <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">Sea Routes</p>
                    <div className="space-y-3">
                      {Object.entries(routeSettings.sea_routes).map(([name, wps]) => (
                        <RouteCard
                          key={name}
                          category="sea_routes"
                          name={name}
                          waypoints={wps}
                          onSave={handleSaveRoute}
                          onReset={handleResetRoute}
                        />
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">Arctic Routes</p>
                    <div className="space-y-3">
                      {Object.entries(routeSettings.arctic_routes).map(([name, wps]) => (
                        <RouteCard
                          key={name}
                          category="arctic_routes"
                          name={name}
                          waypoints={wps}
                          onSave={handleSaveRoute}
                          onReset={handleResetRoute}
                        />
                      ))}
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── TCO tab ── */}
          {activeTab === 'tco' && (
            <div className="space-y-5">
              <p className="text-xs text-gray-500">
                Business model parameters used to compute Total Cost of Ownership (TCO) over the
                mission lifetime. All monetary values are in USD millions ($M) unless noted.
                Changes apply to all future simulations.
              </p>
              {tcoLoading && <p className="text-sm text-gray-500 animate-pulse">Loading TCO config…</p>}
              {tcoError   && <p className="text-sm text-red-400">Failed to load TCO configuration.</p>}

              {tco && (
                <>
                  {/* Satellite platforms */}
                  <TcoSection title="Satellite Platforms">
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="text-gray-500 border-b border-gray-800">
                            <th className="text-left pb-2 font-medium">Platform</th>
                            <th className="text-right pb-2 font-medium w-36">Unit Cost ($M)</th>
                            <th className="text-right pb-2 font-medium w-36">Typical Mass (kg)</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-800">
                          {Object.entries(tco.satellite_platforms).map(([name, p]) => (
                            <tr key={name}>
                              <td className="py-2 text-gray-300 font-mono">{name}</td>
                              <td className="py-2">
                                <NumInput value={p.unit_cost} onChange={(v) =>
                                  setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.satellite_platforms[name].unit_cost = v; return n })
                                } />
                              </td>
                              <td className="py-2">
                                <NumInput value={p.typical_mass_kg} onChange={(v) =>
                                  setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.satellite_platforms[name].typical_mass_kg = v; return n })
                                } />
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </TcoSection>

                  {/* Payload multipliers */}
                  <TcoSection title="Payload Cost Multipliers">
                    <p className="text-xs text-gray-600 mb-3">Multiplied against the satellite platform unit cost</p>
                    <div className="grid grid-cols-2 gap-x-8 gap-y-2">
                      {Object.entries(tco.payload_multipliers).map(([tech, val]) => (
                        <TcoRow key={tech} label={tech.toUpperCase()} unit="×" value={val}
                          onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.payload_multipliers[tech] = v; return n })}
                        />
                      ))}
                    </div>
                  </TcoSection>

                  {/* Launch vehicles */}
                  <TcoSection title="Launch Vehicles">
                    <div className="space-y-4">
                      {Object.entries(tco.launch_vehicles).map(([name, lv]) => (
                        <div key={name} className="border border-gray-800 rounded-lg p-3">
                          <p className="text-xs font-mono text-indigo-300 mb-2">{name}</p>
                          <div className="grid grid-cols-2 gap-x-8 gap-y-1.5">
                            {'base_cost' in lv && (
                              <TcoRow label="Base cost" unit={M} value={lv.base_cost!}
                                onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); (n.launch_vehicles[name] as any).base_cost = v; return n })}
                              />
                            )}
                            {'cost_per_kg' in lv && (
                              <TcoRow label="Cost per kg" unit="$M/kg" value={lv.cost_per_kg!}
                                onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); (n.launch_vehicles[name] as any).cost_per_kg = v; return n })}
                              />
                            )}
                            {'cost_per_launch' in lv && (
                              <TcoRow label="Cost per launch" unit={M} value={lv.cost_per_launch!}
                                onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); (n.launch_vehicles[name] as any).cost_per_launch = v; return n })}
                              />
                            )}
                            <TcoRow label="Max payload" unit="kg" value={lv.max_payload_kg}
                              onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.launch_vehicles[name].max_payload_kg = v; return n })}
                            />
                            <TcoRow label="Batch size" unit="sats" value={lv.typical_batch_size}
                              onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.launch_vehicles[name].typical_batch_size = v; return n })}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </TcoSection>

                  {/* Development costs */}
                  <TcoSection title="Development Costs (CAPEX one-time)">
                    <div className="space-y-1.5">
                      <TcoRow label="Initial R&D" unit={M} value={tco.development.initial_rd}
                        onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.development.initial_rd = v; return n })}
                      />
                      <TcoRow label="Payload development" unit={M} value={tco.development.payload_development}
                        onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.development.payload_development = v; return n })}
                      />
                      <TcoRow label="Ground segment" unit={M} value={tco.development.ground_segment}
                        onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.development.ground_segment = v; return n })}
                      />
                    </div>
                  </TcoSection>

                  {/* Operations */}
                  <TcoSection title="Operations">
                    <div className="space-y-4">
                      <div>
                        <p className="text-xs text-gray-500 mb-2">Ground stations</p>
                        <div className="space-y-1.5 pl-3">
                          <TcoRow label="Stations per 100 sats" unit="" value={tco.operations.ground_stations.stations_needed_per_100_sats}
                            onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.operations.ground_stations.stations_needed_per_100_sats = v; return n })}
                          />
                          <TcoRow label="Initial CAPEX / station" unit={M} value={tco.operations.ground_stations.initial_capex}
                            onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.operations.ground_stations.initial_capex = v; return n })}
                          />
                          <TcoRow label="Annual OPEX / station" unit={M+'/yr'} value={tco.operations.ground_stations.annual_opex}
                            onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.operations.ground_stations.annual_opex = v; return n })}
                          />
                        </div>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 mb-2">Mission control</p>
                        <div className="space-y-1.5 pl-3">
                          <TcoRow label="Initial CAPEX" unit={M} value={tco.operations.mission_control.initial_capex}
                            onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.operations.mission_control.initial_capex = v; return n })}
                          />
                          <TcoRow label="Annual OPEX" unit={M+'/yr'} value={tco.operations.mission_control.annual_opex}
                            onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.operations.mission_control.annual_opex = v; return n })}
                          />
                        </div>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500 mb-2">Network operations & staff</p>
                        <div className="space-y-1.5 pl-3">
                          <TcoRow label="Network cost / sat / year" unit={M} value={tco.operations.network_operations.cost_per_sat_per_year}
                            onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.operations.network_operations.cost_per_sat_per_year = v; return n })}
                          />
                          <TcoRow label="Engineers per 100 sats" unit="" value={tco.operations.staff.engineers_per_100_sats}
                            onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.operations.staff.engineers_per_100_sats = v; return n })}
                          />
                          <TcoRow label="Annual cost / engineer" unit={M+'/yr'} value={tco.operations.staff.annual_cost_per_engineer}
                            onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.operations.staff.annual_cost_per_engineer = v; return n })}
                          />
                        </div>
                      </div>
                    </div>
                  </TcoSection>

                  {/* Insurance & Decommissioning */}
                  <div className="grid grid-cols-2 gap-5">
                    <TcoSection title="Insurance">
                      <div className="space-y-1.5">
                        <TcoRow label="Launch insurance" unit={PCT} value={tco.insurance.launch_insurance_pct * 100}
                          onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.insurance.launch_insurance_pct = v / 100; return n })}
                        />
                        <TcoRow label="Annual in-orbit" unit={PCT+'/yr'} value={tco.insurance.annual_in_orbit_pct * 100}
                          onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.insurance.annual_in_orbit_pct = v / 100; return n })}
                        />
                      </div>
                    </TcoSection>
                    <TcoSection title="Decommissioning">
                      <div className="space-y-1.5">
                        <TcoRow label="Cost per satellite" unit={M} value={tco.decommissioning.cost_per_satellite}
                          onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.decommissioning.cost_per_satellite = v; return n })}
                        />
                        <TcoRow label="Regulatory compliance" unit={M} value={tco.decommissioning.regulatory_compliance}
                          onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.decommissioning.regulatory_compliance = v; return n })}
                        />
                      </div>
                    </TcoSection>
                  </div>

                  {/* Deployment modes */}
                  <TcoSection title="Deployment Modes">
                    <div className="space-y-4">
                      {Object.entries(tco.deployment).map(([mode, dp]) => (
                        <div key={mode} className="border border-gray-800 rounded-lg p-3">
                          <p className="text-xs font-mono text-indigo-300 mb-2">{mode}</p>
                          <div className="grid grid-cols-2 gap-x-8 gap-y-1.5">
                            <TcoRow label="Planes per launch" unit="" value={dp.planes_per_launch}
                              onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.deployment[mode].planes_per_launch = v; return n })}
                            />
                            <TcoRow label="Propulsion cost / sat" unit={M} value={dp.propulsion_cost_per_sat}
                              onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.deployment[mode].propulsion_cost_per_sat = v; return n })}
                            />
                            <TcoRow label="OPEX factor" unit="×" value={dp.deployment_opex_factor}
                              onChange={(v) => setTcoDraft((d) => { const n = structuredClone(d ?? tcoSettings!); n.deployment[mode].deployment_opex_factor = v; return n })}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </TcoSection>

                  {/* Save / Reset */}
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={handleSaveTco}
                      disabled={!tcoDraft}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                                 bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors"
                    >
                      <Save className="w-3.5 h-3.5" />
                      Save business model
                    </button>
                    <button
                      onClick={() => mutateResetTco.mutateAsync()}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                                 text-gray-400 bg-gray-800 hover:text-white hover:bg-gray-700 transition-colors"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Reset to defaults
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── Constellations tab ── */}
          {activeTab === 'constellations' && (
            <div className="space-y-6">
              <p className="text-xs text-gray-500">
                Manage constellation geometry presets. Select a preset when creating a new
                simulation to auto-fill satellites, planes, altitude, inclination and phasing.
                Built-in presets can be deleted and restored with "Reset to defaults".
              </p>
              {consLoading && <p className="text-sm text-gray-500 animate-pulse">Loading presets…</p>}
              {consError   && <p className="text-sm text-red-400">Failed to load constellation presets.</p>}

              {constellationPresets && (
                <>
                  {/* Preset table */}
                  <div className="overflow-x-auto rounded-xl border border-gray-800">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="bg-gray-900 text-gray-500 border-b border-gray-800">
                          <th className="text-left px-3 py-2 font-medium">Name</th>
                          <th className="text-right px-3 py-2 font-medium">Sats</th>
                          <th className="text-right px-3 py-2 font-medium">Planes</th>
                          <th className="text-right px-3 py-2 font-medium">Alt (km)</th>
                          <th className="text-right px-3 py-2 font-medium">Inc (°)</th>
                          <th className="text-right px-3 py-2 font-medium">Phase</th>
                          <th className="text-center px-3 py-2 font-medium">SSO</th>
                          <th className="text-left px-3 py-2 font-medium">Default Comms</th>
                          <th className="text-left px-3 py-2 font-medium">Sat. Type</th>
                          <th className="text-left px-3 py-2 font-medium max-w-xs">Description</th>
                          <th className="px-3 py-2" />
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800">
                        {Object.entries(constellationPresets).map(([name, p]) => (
                          <>
                            <tr key={name} className="hover:bg-gray-900 transition-colors">
                              <td className="px-3 py-2 font-mono text-indigo-300 whitespace-nowrap">{name}</td>
                              <td className="px-3 py-2 text-right tabular-nums text-gray-300">{p.sats}</td>
                              <td className="px-3 py-2 text-right tabular-nums text-gray-300">{p.planes}</td>
                              <td className="px-3 py-2 text-right tabular-nums text-gray-300">{p.altitude}</td>
                              <td className="px-3 py-2 text-right tabular-nums text-gray-300">{p.inclination}</td>
                              <td className="px-3 py-2 text-right tabular-nums text-gray-300">{p.phasing}</td>
                              <td className="px-3 py-2 text-center">
                                {p.sso
                                  ? <span className="text-green-400">✓</span>
                                  : <span className="text-gray-700">—</span>}
                              </td>
                              <td className="px-3 py-2 text-gray-400 font-mono text-xs whitespace-nowrap">
                                {p.default_comms || <span className="text-gray-700">—</span>}
                              </td>
                              <td className="px-3 py-2 text-gray-400 font-mono text-xs whitespace-nowrap">
                                {p.default_satellite_type || <span className="text-gray-700">—</span>}
                              </td>
                              <td className="px-3 py-2 text-gray-500 max-w-xs truncate">{p.description}</td>
                              <td className="px-3 py-2">
                                <div className="flex items-center gap-2">
                                  <button
                                    onClick={() => {
                                      if (editingName === name) {
                                        setEditingName(null)
                                        setEditDraft(null)
                                      } else {
                                        setEditingName(name)
                                        setEditDraft({ name, ...p })
                                      }
  const [twofaStatus, setTwofaStatus] = useState<boolean | null>(null)
  const handleToggle2FA = () => setTwofaStatus(!twofaStatus)
                                    }}
                                    className={`transition-colors ${editingName === name ? 'text-indigo-400 hover:text-indigo-300' : 'text-gray-600 hover:text-indigo-400'}`}
                                    title={editingName === name ? 'Cancel edit' : 'Edit preset'}
                                  >
                                    {editingName === name
                                      ? <XIcon className="w-3.5 h-3.5" />
                                      : <Pencil className="w-3.5 h-3.5" />}
                                  </button>
                                  <button
                                    onClick={() => mutateDeleteConstellation.mutateAsync(name)}
                                    className="text-gray-600 hover:text-red-400 transition-colors"
                                    title="Delete preset"
                                  >
                                    <Trash2 className="w-3.5 h-3.5" />
                                  </button>
                                </div>
                              </td>
                            </tr>
                            {editingName === name && editDraft && (
                              <tr key={`${name}-edit`} className="bg-gray-950 border-b border-indigo-900">
                                <td colSpan={11} className="px-4 py-4">
                                  <div className="grid grid-cols-3 gap-x-6 gap-y-3">
                                    <div>
                                      <label className="block text-xs text-gray-500 mb-1">Name</label>
                                      <input
                                        type="text"
                                        value={editDraft.name}
                                        onChange={(e) => setEditDraft((d) => d ? { ...d, name: e.target.value } : d)}
                                        className={inputCls + ' text-left'}
                                      />
                                    </div>
                                    <div>
                                      <label className="block text-xs text-gray-500 mb-1">Satellites</label>
                                      <NumInput value={editDraft.sats} onChange={(v) => setEditDraft((d) => d ? { ...d, sats: Math.round(v) } : d)} />
                                    </div>
                                    <div>
                                      <label className="block text-xs text-gray-500 mb-1">Orbital planes</label>
                                      <NumInput value={editDraft.planes} onChange={(v) => setEditDraft((d) => d ? { ...d, planes: Math.round(v) } : d)} />
                                    </div>
                                    <div>
                                      <label className="block text-xs text-gray-500 mb-1">Altitude (km)</label>
                                      <NumInput value={editDraft.altitude} onChange={(v) => setEditDraft((d) => d ? { ...d, altitude: v } : d)} />
                                    </div>
                                    <div>
                                      <label className="block text-xs text-gray-500 mb-1">Inclination (°)</label>
                                      <NumInput value={editDraft.inclination} onChange={(v) => setEditDraft((d) => d ? { ...d, inclination: v } : d)} />
                                    </div>
                                    <div>
                                      <label className="block text-xs text-gray-500 mb-1">Phasing</label>
                                      <NumInput value={editDraft.phasing} onChange={(v) => setEditDraft((d) => d ? { ...d, phasing: Math.round(v) } : d)} />
                                    </div>
                                    <div className="flex items-center gap-3 pt-3">
                                      <label className="relative inline-flex items-center cursor-pointer">
                                        <input
                                          type="checkbox"
                                          checked={editDraft.sso}
                                          onChange={(e) => setEditDraft((d) => d ? { ...d, sso: e.target.checked, inclination: e.target.checked ? 97.6 : d.inclination } : d)}
                                          className="sr-only peer"
                                        />
                                        <div className="w-9 h-5 bg-gray-700 peer-checked:bg-indigo-600 rounded-full peer
                                                        after:content-[''] after:absolute after:top-[2px] after:left-[2px]
                                                        after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all
                                                        peer-checked:after:translate-x-4" />
                                        <span className="ml-2 text-xs text-gray-400">SSO</span>
                                      </label>
                                    </div>
                                    <div>
                                      <label className="block text-xs text-gray-500 mb-1">Default comms</label>
                                      <select
                                        className={inputCls}
                                        value={editDraft.default_comms ?? ''}
                                        onChange={(e) => setEditDraft((d) => d ? { ...d, default_comms: e.target.value } : d)}
                                      >
                                        <option value="">— no default —</option>
                                        {commsList.map((c) => <option key={c}>{c}</option>)}
                                      </select>
                                    </div>
                                    <div>
                                      <label className="block text-xs text-gray-500 mb-1">Satellite type</label>
                                      <select
                                        className={inputCls}
                                        value={editDraft.default_satellite_type ?? ''}
                                        onChange={(e) => setEditDraft((d) => d ? { ...d, default_satellite_type: e.target.value } : d)}
                                      >
                                        <option value="">— no default —</option>
                                        {platformsList.map((c) => <option key={c}>{c}</option>)}
                                      </select>
                                    </div>
                                    <div className="col-span-3">
                                      <label className="block text-xs text-gray-500 mb-1">Description</label>
                                      <input
                                        type="text"
                                        value={editDraft.description}
                                        onChange={(e) => setEditDraft((d) => d ? { ...d, description: e.target.value } : d)}
                                        className={inputCls + ' text-left'}
                                      />
                                    </div>
                                  </div>
                                  <div className="flex gap-2 mt-4 pt-3 border-t border-gray-800">
                                    <button
                                      disabled={!editDraft.name.trim()}
                                      onClick={() => mutateSaveConstellation.mutateAsync(editDraft as unknown as Record<string, unknown>)}
                                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                                                 bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors"
                                    >
                                      <Check className="w-3.5 h-3.5" />
                                      Save changes
                                    </button>
                                    <button
                                      onClick={() => { setEditingName(null); setEditDraft(null) }}
                                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                                                 text-gray-400 bg-gray-800 hover:text-white hover:bg-gray-700 transition-colors"
                                    >
                                      <XIcon className="w-3.5 h-3.5" />
                                      Cancel
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Add new preset form */}
                  <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
                    <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
                      <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                      Add constellation preset
                    </p>
                    <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                      <div className="col-span-2">
                        <label className="block text-xs text-gray-500 mb-1">Name <span className="text-red-500">*</span></label>
                        <input
                          type="text"
                          value={newPreset.name}
                          onChange={(e) => setNewPreset((d) => ({ ...d, name: e.target.value }))}
                          placeholder="e.g. my_leo_12"
                          className={inputCls + ' text-left'}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Satellites</label>
                        <NumInput value={newPreset.sats} onChange={(v) => setNewPreset((d) => ({ ...d, sats: Math.round(v) }))} />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Orbital planes</label>
                        <NumInput value={newPreset.planes} onChange={(v) => setNewPreset((d) => ({ ...d, planes: Math.round(v) }))} />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Altitude (km)</label>
                        <NumInput value={newPreset.altitude} onChange={(v) => setNewPreset((d) => ({ ...d, altitude: v }))} />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Inclination (°)</label>
                        <NumInput value={newPreset.inclination} onChange={(v) => setNewPreset((d) => ({ ...d, inclination: v }))} />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Phasing</label>
                        <NumInput value={newPreset.phasing} onChange={(v) => setNewPreset((d) => ({ ...d, phasing: Math.round(v) }))} />
                      </div>
                      <div className="flex items-center gap-3 pt-4">
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input
                            type="checkbox"
                            checked={newPreset.sso}
                            onChange={(e) => setNewPreset((d) => ({ ...d, sso: e.target.checked, inclination: e.target.checked ? 97.6 : d.inclination }))}
                            className="sr-only peer"
                          />
                          <div className="w-9 h-5 bg-gray-700 peer-checked:bg-indigo-600 rounded-full peer
                                          after:content-[''] after:absolute after:top-[2px] after:left-[2px]
                                          after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all
                                          peer-checked:after:translate-x-4" />
                          <span className="ml-2 text-xs text-gray-400">Sun-synchronous (SSO)</span>
                        </label>
                      </div>
                      <div className="col-span-2">
                        <label className="block text-xs text-gray-500 mb-1">Description</label>
                        <input
                          type="text"
                          value={newPreset.description}
                          onChange={(e) => setNewPreset((d) => ({ ...d, description: e.target.value }))}
                          placeholder="Short description of the constellation"
                          className={inputCls + ' text-left'}
                        />
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Default comms</label>
                        <select
                          className={inputCls}
                          value={newPreset.default_comms ?? ''}
                          onChange={(e) => setNewPreset((d) => ({ ...d, default_comms: e.target.value }))}
                        >
                          <option value="">— no default —</option>
                          {commsList.map((c) => <option key={c}>{c}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs text-gray-500 mb-1">Satellite type</label>
                        <select
                          className={inputCls}
                          value={newPreset.default_satellite_type ?? ''}
                          onChange={(e) => setNewPreset((d) => ({ ...d, default_satellite_type: e.target.value }))}
                        >
                          <option value="">— no default —</option>
                          {platformsList.map((c) => <option key={c}>{c}</option>)}
                        </select>
                      </div>
                    </div>
                    <button
                      disabled={!newPreset.name.trim()}
                      onClick={() => mutateSaveConstellation.mutateAsync(newPreset as unknown as Record<string, unknown>)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                                 bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors"
                    >
                      <Plus className="w-3.5 h-3.5" />
                      Add preset
                    </button>
                  </div>

                  {/* Reset all */}
                  <div className="flex justify-end">
                    <button
                      onClick={() => mutateResetConstellations.mutateAsync()}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                                 text-gray-400 bg-gray-800 hover:text-white hover:bg-gray-700 transition-colors"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      Reset to defaults
                    </button>
                  </div>

                  {/* ── Multi-shell groups ── */}
                  <div className="mt-8 pt-6 border-t border-gray-800 space-y-4">
                    <div className="flex items-center justify-between">
                      <p className="text-xs font-semibold text-violet-400 uppercase tracking-wider flex items-center gap-2">
                        <Sparkles className="w-3.5 h-3.5" />
                        Multi-Shell Constellations
                      </p>
                      <button
                        onClick={() => mutateResetMultiShell.mutateAsync()}
                        className="flex items-center gap-1 px-2.5 py-1 rounded text-xs text-gray-500 bg-gray-800 hover:text-white hover:bg-gray-700 transition-colors"
                      >
                        <RotateCcw className="w-3 h-3" /> Reset built-ins
                      </button>
                    </div>
                    <p className="text-xs text-gray-500">
                      Define groups of shells. Each group appears in the Orbit Animation
                      "Named multi-shell preset" dropdown. Built-in groups (from the simulator)
                      are shown in grey and can be deleted.
                    </p>

                    {msLoading && <p className="text-xs text-gray-500 animate-pulse">Loading groups…</p>}

                    {multiShellGroups && Object.keys(multiShellGroups).length > 0 && (
                      <div className="overflow-x-auto rounded-xl border border-gray-800">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="bg-gray-900 text-gray-500 border-b border-gray-800">
                              <th className="text-left px-3 py-2 font-medium">Name</th>
                              <th className="text-right px-3 py-2 font-medium">Shells</th>
                              <th className="text-right px-3 py-2 font-medium">Total sats</th>
                              <th className="text-left px-3 py-2 font-medium">Default Comms</th>
                              <th className="text-left px-3 py-2 font-medium">Sat. Type</th>
                              <th className="text-left px-3 py-2 font-medium">Description</th>
                              <th className="px-3 py-2" />
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-800">
                            {Object.entries(multiShellGroups).map(([name, g]) => (
                              <tr key={name} className="hover:bg-gray-900 transition-colors">
                                <td className="px-3 py-2 font-mono whitespace-nowrap"
                                    style={{ color: g.builtin ? '#a78bfa' : '#818cf8' }}>{name}</td>
                                <td className="px-3 py-2 text-right tabular-nums text-gray-300">{g.shells.length}</td>
                                <td className="px-3 py-2 text-right tabular-nums text-gray-300">
                                  {g.shells.reduce((acc, s) => acc + (s.sats || 0), 0)}
                                </td>
                                <td className="px-3 py-2 text-gray-400 font-mono text-xs whitespace-nowrap">
                                  {g.default_comms || <span className="text-gray-700">—</span>}
                                </td>
                                <td className="px-3 py-2 text-gray-400 font-mono text-xs whitespace-nowrap">
                                  {g.default_satellite_type || <span className="text-gray-700">—</span>}
                                </td>
                                <td className="px-3 py-2 text-gray-500 max-w-xs truncate">{g.description}</td>
                                <td className="px-3 py-2">
                                  <div className="flex items-center justify-end gap-2">
                                    <button
                                      onClick={() => startEditMultiShell(name, g)}
                                      className="text-gray-600 hover:text-violet-400 transition-colors"
                                      title="Edit group"
                                    >
                                      <Pencil className="w-3.5 h-3.5" />
                                    </button>
                                    <button
                                      onClick={() => mutateDeleteMultiShell.mutateAsync(name)}
                                      className="text-gray-600 hover:text-red-400 transition-colors"
                                      title={g.builtin ? 'Hide built-in group' : 'Delete group'}
                                    >
                                      <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                  </div>
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {/* Add multi-shell group form */}
                    <div id="multi-shell-form" className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
                      <div className="flex items-center justify-between">
                        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
                          {msEditingName ? `Edit “${msEditingName}”` : 'Create multi-shell group'}
                        </p>
                        {msEditingName && (
                          <button
                            onClick={cancelEditMultiShell}
                            className="text-xs text-gray-500 hover:text-white"
                          >Cancel</button>
                        )}
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="col-span-2">
                          <label className="block text-xs text-gray-500 mb-1">Group name <span className="text-red-500">*</span></label>
                          <input type="text" value={msName} onChange={(e) => setMsName(e.target.value)}
                            placeholder="e.g. my_leo_group" className={inputCls + ' text-left'} />
                        </div>
                        <div className="col-span-2">
                          <label className="block text-xs text-gray-500 mb-1">Description</label>
                          <input type="text" value={msDesc} onChange={(e) => setMsDesc(e.target.value)}
                            placeholder="Short description" className={inputCls + ' text-left'} />
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Default comms</label>
                          <select
                            className={inputCls}
                            value={msDefaultComms}
                            onChange={(e) => setMsDefaultComms(e.target.value)}
                          >
                            <option value="">— no default —</option>
                            {commsList.map((c) => <option key={c}>{c}</option>)}
                          </select>
                        </div>
                        <div>
                          <label className="block text-xs text-gray-500 mb-1">Satellite type</label>
                          <select
                            className={inputCls}
                            value={msDefaultSatType}
                            onChange={(e) => setMsDefaultSatType(e.target.value)}
                          >
                            <option value="">— no default —</option>
                            {platformsList.map((c) => <option key={c}>{c}</option>)}
                          </select>
                        </div>
                      </div>

                      {/* Shells editor */}
                      <div className="space-y-2">
                        <p className="text-xs text-gray-500 font-medium">Shells</p>
                        {msShells.map((sh, idx) => (
                          <div key={sh._key} className="flex gap-2 items-end flex-wrap bg-gray-800/50 rounded-lg p-2">
                            <div className="flex-1 min-w-[80px]">
                              <label className="block text-xs text-gray-600 mb-0.5">Shell name</label>
                              <input type="text" value={sh.name ?? ''}
                                onChange={(e) => updateMsShell(sh._key, 'name', e.target.value)}
                                placeholder={`Shell ${idx + 1}`}
                                className="w-full px-2 py-1 rounded bg-gray-800 border border-gray-700 text-xs text-white focus:outline-none focus:ring-1 focus:ring-violet-500" />
                            </div>
                            <div className="w-16">
                              <label className="block text-xs text-gray-600 mb-0.5">Sats</label>
                              <NumInput value={sh.sats} onChange={(v) => updateMsShell(sh._key, 'sats', Math.round(v))} />
                            </div>
                            <div className="w-16">
                              <label className="block text-xs text-gray-600 mb-0.5">Planes</label>
                              <NumInput value={sh.planes} onChange={(v) => updateMsShell(sh._key, 'planes', Math.round(v))} />
                            </div>
                            <div className="w-20">
                              <label className="block text-xs text-gray-600 mb-0.5">Alt (km)</label>
                              <NumInput value={sh.altitude_km} onChange={(v) => updateMsShell(sh._key, 'altitude_km', v)} />
                            </div>
                            <div className="w-16">
                              <label className="block text-xs text-gray-600 mb-0.5">Inc (°)</label>
                              <NumInput value={sh.inclination} onChange={(v) => updateMsShell(sh._key, 'inclination', v)} />
                            </div>
                            <div className="w-14">
                              <label className="block text-xs text-gray-600 mb-0.5">Phasing</label>
                              <NumInput value={sh.phasing} onChange={(v) => updateMsShell(sh._key, 'phasing', Math.round(v))} />
                            </div>
                            {msShells.length > 1 && (
                              <button onClick={() => removeMsShell(sh._key)}
                                className="text-gray-600 hover:text-red-400 transition-colors pb-1">
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        ))}
                        <button onClick={addMsShell}
                          className="flex items-center gap-1 text-xs text-gray-500 hover:text-violet-400 transition-colors">
                          <Plus className="w-3 h-3" /> Add shell
                        </button>
                      </div>

                      <button
                        disabled={!msName.trim() || msShells.length === 0}
                        onClick={() => {
                          const body = {
                            name: msName.trim(),
                            shells: msShells.map(({ _key, ...s }) => s),
                            description: msDesc,
                            ...(msDefaultComms     ? { default_comms:          msDefaultComms }     : {}),
                            ...(msDefaultSatType   ? { default_satellite_type: msDefaultSatType }   : {}),
                          }
                          if (msEditingName) {
                            return mutateUpdateMultiShell.mutateAsync({ name: msEditingName, body })
                          }
                          return mutateSaveMultiShell.mutateAsync(body)
                        }}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                                   bg-violet-600 text-white hover:bg-violet-500 disabled:opacity-40 transition-colors"
                      >
                        <Plus className="w-3.5 h-3.5" />
                        {msEditingName ? 'Update group' : 'Save group'}
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          )}

          {/* ── AI Assistant tab ── */}
          {activeTab === 'ai' && (
            <div className="space-y-5">
              <div className="flex items-center gap-2 mb-1">
                <Brain className="w-4 h-4 text-indigo-400" />
                <p className="text-sm font-medium text-white">AI Assistant configuration</p>
                {aiOk
                  ? <span className="flex items-center gap-1 text-xs text-emerald-400 bg-emerald-900/30 border border-emerald-700/40 px-2 py-0.5 rounded-full">
                      <ShieldCheck className="w-3 h-3" /> Key configured
                    </span>
                  : <span className="text-xs text-yellow-400 bg-yellow-900/30 border border-yellow-700/40 px-2 py-0.5 rounded-full">No key set</span>
                }
              </div>
              <div className="flex items-start gap-2 bg-indigo-950/30 border border-indigo-800/40 rounded-lg p-3">
                <ShieldCheck className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
                <p className="text-xs text-indigo-300">
                  The API key is stored server-side only and is never sent to the browser.
                  The LLM is called from the server — your key cannot be intercepted from the network tab.
                </p>
              </div>

              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
                {/* Base URL */}
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-400">Base URL</label>
                  <input
                    type="url"
                    value={aiDraft.base_url}
                    onChange={(e) => setAiDraft((d) => ({ ...d, base_url: e.target.value }))}
                    placeholder="https://api.openai.com/v1"
                    className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm
                               text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500"
                  />
                  <p className="text-xs text-gray-600">Ollama: http://localhost:11434/v1 · Azure: https://&lt;resource&gt;.openai.azure.com/openai/deployments/&lt;deployment&gt;</p>
                </div>

                {/* Model */}
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-400">Model</label>
                  <input
                    type="text"
                    value={aiDraft.model}
                    onChange={(e) => setAiDraft((d) => ({ ...d, model: e.target.value }))}
                    placeholder="gpt-4o"
                    className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm
                               text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500"
                  />
                  <p className="text-xs text-gray-600">e.g. gpt-4o · gpt-4o-mini · llama3 · mistral</p>
                </div>

                {/* API Key — write-only */}
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-400">API Key</label>
                  <div className="flex items-center gap-2">
                    <input
                      type="password"
                      value={aiDraft.api_key}
                      onChange={(e) => setAiDraft((d) => ({ ...d, api_key: e.target.value }))}
                      placeholder={aiStatus.maskedKey || 'Enter new key…'}
                      className="flex-1 bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm
                                 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
                    />
                    {aiOk && (
                      <span className="text-xs text-gray-500 font-mono whitespace-nowrap">
                        current: {aiStatus.maskedKey}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-600">
                    Leave blank to keep the existing key. The raw key is never returned to the browser.
                  </p>
                </div>

                {/* System prompt */}
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-400">System prompt</label>
                  <textarea
                    rows={6}
                    value={aiDraft.system_prompt}
                    onChange={(e) => setAiDraft((d) => ({ ...d, system_prompt: e.target.value }))}
                    className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-xs
                               text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500
                               font-mono leading-relaxed resize-y"
                  />
                </div>

                <div className="flex gap-2 pt-1 border-t border-gray-800">
                  <button
                    onClick={saveAiSettings}
                    disabled={aiSaving}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                               bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors"
                  >
                    <Save className="w-3.5 h-3.5" />
                    {aiSaving ? 'Saving…' : aiSaved ? 'Saved ✓' : 'Save to server'}
                  </button>
                </div>
              </div>

              {/* ── CARL Configuration ── */}
              <CarlConfigSection />

              {/* ── Two-Factor Authentication ── */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-indigo-400" />
                  <p className="text-sm font-medium text-white">Two-Factor Authentication</p>
                </div>
                <p className="text-xs text-gray-500">
                  Add an extra layer of security. When enabled, you will need a verification code sent to your email
                  in addition to your password when signing in.
                </p>
                {twofaStatus !== null && (
                  <div className="flex items-center gap-3">
                    <button onClick={handleToggle2FA}
                      className={"px-4 py-1.5 rounded-lg text-xs font-medium transition-colors " + (
                        twofaStatus ? "bg-red-600/20 text-red-400 border border-red-700/50 hover:bg-red-600/30"
                                   : "bg-indigo-600 text-white hover:bg-indigo-500"
                      )}>
                      {twofaStatus ? "Disable 2FA" : "Enable 2FA"}
                    </button>
                    <span className={"text-xs " + (twofaStatus ? "text-emerald-400" : "text-gray-500")}>
                      {twofaStatus ? "Active" : "Inactive"}
                    </span>
                  </div>
                )}
              </div>

              {/* ── Report Sharing ── */}
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4 mt-2">
                <div className="flex items-center gap-2">
                  <Share2 className="w-4 h-4 text-indigo-400" />
                  <p className="text-sm font-medium text-white">Report Sharing — Default Password</p>
                  {shareHasDefault && (
                    <span className="text-xs text-emerald-400 bg-emerald-900/30 border border-emerald-700/40 px-2 py-0.5 rounded-full flex items-center gap-1">
                      <ShieldCheck className="w-3 h-3" /> Password set
                    </span>
                  )}
                </div>
                <p className="text-xs text-gray-500">
                  When you share a report, the Share dialog will pre-fill with this password so you don't
                  have to type it every time. You can always override it per-report.
                </p>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-gray-400">Default share password</label>
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-2 flex-1 bg-gray-800 border border-gray-700 rounded-md px-3 py-2">
                      <Lock className="w-3.5 h-3.5 text-gray-500 flex-shrink-0" />
                      <input
                        type="password"
                        value={sharePwd}
                        onChange={(e) => setSharePwd(e.target.value)}
                        onKeyDown={(e) => { if (e.key === 'Enter') saveSharePassword() }}
                        placeholder={shareHasDefault ? 'Enter new password to update…' : 'Set a default password…'}
                        className="flex-1 bg-transparent text-sm text-white placeholder-gray-600 focus:outline-none"
                      />
                    </div>
                  </div>
                  {shareError && <p className="text-xs text-red-400">{shareError}</p>}
                </div>
                <div className="flex gap-2 pt-1 border-t border-gray-800">
                  <button
                    onClick={saveSharePassword}
                    disabled={shareSaving}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                               bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors"
                  >
                    <Save className="w-3.5 h-3.5" />
                    {shareSaving ? 'Saving…' : shareSaved ? 'Saved ✓' : 'Save password'}
                  </button>
                  {shareHasDefault && (
                    <button
                      onClick={() => { setSharePwd(''); saveSharePassword() }}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                                 text-gray-400 bg-gray-800 hover:text-white hover:bg-gray-700 transition-colors"
                    >
                      Clear password
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
// ── CARL Configuration Section ───────────────────────────────────────────

function CarlConfigSection() {
  const [config, setConfig] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [persona, setPersona] = useState('')
  const [temperature, setTemperature] = useState(0.5)
  const [maxTools, setMaxTools] = useState(5)
  const [tools, setTools] = useState<Record<string, boolean>>({})
  const [carlName, setCarlName] = useState('CARL')

  const TOOL_LABELS: Record<string, string> = {
    submit_simulation: 'Submit simulations',
    submit_batch_sweep: 'Batch sweep',
    get_job_status: 'Query job results',
    read_csv_data: 'Read CSV/GeoJSON files',
    get_simulation_options: 'List simulation options',
    upload_file: 'Upload files for analysis',
  }

  useEffect(() => {
    getCarlConfig().then((cfg) => {
      setConfig(cfg)
      setCarlName(cfg.name || 'CARL')
      setPersona(cfg.persona || '')
      setTemperature(cfg.temperature ?? 0.5)
      setMaxTools(cfg.max_tools_per_turn ?? 5)
      setTools(cfg.tools || {})
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await updateCarlConfig({ name: carlName, persona, temperature, max_tools_per_turn: maxTools, tools })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch { setSaved(false) }
    setSaving(false)
  }

  const restoreDefaults = () => {
    setCarlName('CARL')
    setPersona("You are CARL (Constellation AI Reasoning Layer), an AI constellation engineer inspired by Carl Sagan. You make complex orbital mechanics accessible and exciting. You have direct access to the Constellation Simulator API. Create simulations, analyze results, and iterate on designs. Explain your reasoning in clear, vivid terms. Always use metric units (km, degrees, dB). Be technical but not dry.")
    setTemperature(0.5)
    setMaxTools(5)
    setTools({
      submit_simulation: true, submit_batch_sweep: true, get_job_status: true,
      read_csv_data: true, get_simulation_options: true, upload_file: true,
    })
  }

  if (loading) return <div className="text-gray-400 text-sm p-4">Loading CARL config...</div>

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-2">
        <Bot className="w-4 h-4 text-indigo-400" />
        <p className="text-sm font-medium text-white">CARL — Constellation AI Reasoning Layer</p>
      </div>
      <p className="text-xs text-gray-500">
        Configure CARL's personality, capabilities (tools), and creativity. These settings affect how
        CARL responds and which actions it can perform. Changes take effect immediately.
      </p>

      {/* Name & Temperature */}
      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-400">Name</label>
          <input value={carlName} onChange={e => setCarlName(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-400">Temperature (0.0–1.0)</label>
          <input type="number" min={0} max={1} step={0.1} value={temperature}
            onChange={e => setTemperature(parseFloat(e.target.value) || 0.5)}
            className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" />
        </div>
        <div className="space-y-1">
          <label className="text-xs font-medium text-gray-400">Max tools per turn</label>
          <input type="number" min={1} max={20} step={1} value={maxTools}
            onChange={e => setMaxTools(parseInt(e.target.value) || 5)}
            className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500" />
        </div>
      </div>

      {/* Persona */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <label className="text-xs font-medium text-gray-400">Persona (System Prompt)</label>
          <button onClick={restoreDefaults}
            className="text-xs text-gray-500 hover:text-gray-300 underline">Restore default</button>
        </div>
        <textarea value={persona} onChange={e => setPersona(e.target.value)} rows={6}
          className="w-full bg-gray-800 border border-gray-700 rounded-md px-3 py-2 text-xs text-white
                     focus:outline-none focus:border-indigo-500 font-mono leading-relaxed resize-y" />
      </div>

      {/* Tools */}
      <div className="space-y-2">
        <label className="text-xs font-medium text-gray-400">Capabilities (tools CARL can use)</label>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
          {Object.entries(TOOL_LABELS).map(([key, label]) => (
            <label key={key} className="flex items-center gap-2 cursor-pointer">
              <input type="checkbox" checked={tools[key] ?? true}
                onChange={e => setTools({ ...tools, [key]: e.target.checked })}
                className="accent-indigo-500" />
              <span className="text-sm text-gray-300">{label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Save */}
      <div className="flex items-center gap-3 pt-1 border-t border-gray-800">
        <button onClick={handleSave} disabled={saving}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium
                     bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors">
          <Save className="w-3.5 h-3.5" />
          {saving ? 'Saving...' : saved ? 'Saved ✓' : 'Save CARL Config'}
        </button>
      </div>
    </div>
  )
}