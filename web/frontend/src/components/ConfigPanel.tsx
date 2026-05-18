import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchOptions, submitJob } from '../api/client'
import type { JobMode, OptionsResponse, ConstellationPreset, MultiShellPreset, ShellDef } from '../types'
import { Play, ChevronDown, Sparkles, FileText } from 'lucide-react'
import ReportConfirmModal from './ReportConfirmModal'

// ── Small field helpers ────────────────────────────────────────────────────────

type FieldProps = {
  label: string
  hint?: string
  children: React.ReactNode
}
function Field({ label, hint, children }: FieldProps) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-400 mb-1">
        {label}
        {hint && <span className="ml-1 text-gray-600">({hint})</span>}
      </label>
      {children}
    </div>
  )
}

const inputCls =
  'w-full px-2.5 py-1.5 rounded-md bg-gray-800 border border-gray-700 text-sm text-white ' +
  'focus:outline-none focus:ring-1 focus:ring-indigo-500'

const selectCls = inputCls

function NumberField({
  label, hint, value, onChange, min, max, step = 1,
}: {
  label: string; hint?: string; value: number
  onChange: (v: number) => void; min?: number; max?: number; step?: number
}) {
  return (
    <Field label={label} hint={hint}>
      <input
        type="number" className={inputCls} value={value} step={step}
        min={min} max={max}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </Field>
  )
}

function SelectField({
  label, hint, value, options, onChange,
}: {
  label: string; hint?: string; value: string
  options: string[]; onChange: (v: string) => void
}) {
  return (
    <Field label={label} hint={hint}>
      <select className={selectCls} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => <option key={o}>{o}</option>)}
      </select>
    </Field>
  )
}

function Toggle({
  label, value, onChange,
}: { label: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <div
        className={`relative w-9 h-5 rounded-full transition-colors ${value ? 'bg-indigo-600' : 'bg-gray-700'}`}
        onClick={() => onChange(!value)}
      >
        <span
          className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${value ? 'translate-x-4' : ''}`}
        />
      </div>
      <span className="text-sm text-gray-300">{label}</span>
    </label>
  )
}

// ── Default param values ───────────────────────────────────────────────────────

const defaultConstellation = {
  sats: 66, planes: 6, altitude: 600, phasing: 1, inclination: 87.4, sso: false,
  backend: 'matplotlib',
}

// Multi-shell defaults mixed into mode defaults
const multiShellDefaults = {
  constellation: null, constellation_name: null, shells: null, max_sats: 250,
}

type SetFn = (key: string, val: unknown) => void

// ── Mode sections (constellation picker lives in the main component) ──────────

function HeatmapFields({ p, set, opts }: { p: Record<string, unknown>; set: SetFn; opts: OptionsResponse }) {
  const isMultiActive = !!(p.constellation as string) || ((p.shells as ShellDef[]) ?? []).length > 0
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <SelectField label="Comms" value={p.comms as string} options={opts.comms_payloads} onChange={(v) => set('comms', v)} />
        <SelectField label="Sat type" value={p.platform as string} options={opts.platforms} onChange={(v) => set('platform', v)} />
        <SelectField label="Weather" value={p.weather as string} options={opts.weather_scenarios} onChange={(v) => set('weather', v)} />
        <NumberField label="Resolution" hint="°" value={p.res as number} min={0.5} max={20} step={0.5} onChange={(v) => set('res', v)} />
        <NumberField label="Min elevation" hint="°" value={p.min_elev as number} min={0} max={90} onChange={(v) => set('min_elev', v)} />
        {isMultiActive && (
          <NumberField label="Max sats" value={(p.max_sats as number) ?? 250} min={10} max={10000} onChange={(v) => set('max_sats', v)} />
        )}
      </div>
      <Toggle label="Bidirectional" value={p.bidi as boolean} onChange={(v) => set('bidi', v)} />
    </div>
  )
}

function SkyFields({ p, set, opts }: { p: Record<string, unknown>; set: SetFn; opts: OptionsResponse }) {
  const isMultiActive = !!(p.constellation as string) || ((p.shells as ShellDef[]) ?? []).length > 0
  return (
    <div className="space-y-3">
      <SelectField label="Location" value={p.location as string} options={opts.locations} onChange={(v) => set('location', v)} />
      <Toggle label="Coverage pass" value={p.coverage as boolean} onChange={(v) => set('coverage', v)} />
      <div className="grid grid-cols-2 gap-3">
        <SelectField label="Comms" value={p.comms as string} options={opts.comms_payloads} onChange={(v) => set('comms', v)} />
        <SelectField label="Sat type" value={p.platform as string} options={opts.platforms} onChange={(v) => set('platform', v)} />
        <SelectField label="Weather" value={p.weather as string} options={opts.weather_scenarios} onChange={(v) => set('weather', v)} />
        <NumberField label="Duration" hint="h" value={p.duration as number} min={1} max={168} onChange={(v) => set('duration', v)} />
        <NumberField label="Speed" hint="×" value={p.speed as number} min={1} max={3600} onChange={(v) => set('speed', v)} />
        {isMultiActive && (
          <NumberField label="Max sats" value={(p.max_sats as number) ?? 250} min={10} max={10000} onChange={(v) => set('max_sats', v)} />
        )}
      </div>
      <div className="grid grid-cols-2 gap-x-4">
        <Toggle label="Bidirectional" value={p.bidi as boolean} onChange={(v) => set('bidi', v)} />
        <Toggle label="Trails" value={p.trails as boolean} onChange={(v) => set('trails', v)} />
      </div>
    </div>
  )
}

function OrbitFields({ p, set, opts }: { p: Record<string, unknown>; set: SetFn; opts: OptionsResponse }) {
  const isMultiActive = !!(p.constellation as string) || ((p.shells as ShellDef[]) ?? []).length > 0
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <SelectField label="Comms" value={p.comms as string} options={opts.comms_payloads} onChange={(v) => set('comms', v)} />
        <SelectField label="Sat type" value={p.platform as string} options={opts.platforms} onChange={(v) => set('platform', v)} />
        <NumberField label="Min elevation" hint="°" value={p.min_elev as number} min={0} max={90} onChange={(v) => set('min_elev', v)} />
        <NumberField label="Duration" hint="h" value={p.duration as number} min={1} max={168} onChange={(v) => set('duration', v)} />
        {isMultiActive && (
          <NumberField label="Max sats" value={(p.max_sats as number) ?? 250} min={10} max={10000} onChange={(v) => set('max_sats', v)} />
        )}
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-2">
        <Toggle label="Trails"          value={p.trails as boolean}           onChange={(v) => set('trails', v)} />
        <Toggle label="Map"             value={p.map as boolean}              onChange={(v) => set('map', v)} />
        <Toggle label="Beam footprints" value={p.beams as boolean}            onChange={(v) => set('beams', v)} />
        <Toggle label="Coverage fill"   value={(p.fill as boolean) ?? false}  onChange={(v) => set('fill', v)} />
      </div>
    </div>
  )
}

function TrackFields({ p, set }: { p: Record<string, unknown>; set: SetFn; opts: OptionsResponse }) {
  return (
    <div className="grid grid-cols-2 gap-3 items-end">
      <NumberField label="Duration" hint="h" value={p.duration as number} min={1} max={168} onChange={(v) => set('duration', v)} />
      <div className="pb-1"><Toggle label="Map" value={p.map as boolean} onChange={(v) => set('map', v)} /></div>
    </div>
  )
}

const DEFAULT_REPORT_ROUTES = ['titan_corridor', 'roaring_passage', 'borealis_run']

function FullReportFields({ p, set, opts }: { p: Record<string, unknown>; set: SetFn; opts: OptionsResponse }) {
  const allRoutes = [...opts.sea_routes, ...opts.arctic_routes]
  const selected  = (p.reportRoutes as string[]) ?? DEFAULT_REPORT_ROUTES

  function toggle(route: string) {
    const next = selected.includes(route)
      ? selected.filter((r) => r !== route)
      : [...selected, route]
    set('reportRoutes', next)
  }

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <SelectField label="Comms" value={p.comms as string} options={opts.comms_payloads} onChange={(v) => set('comms', v)} />
        <SelectField label="Sat type" value={p.platform as string} options={opts.platforms} onChange={(v) => set('platform', v)} />
      </div>
      <Field label="Routes to analyse">
        <div className="space-y-1.5 mt-1 max-h-40 overflow-y-auto pr-1">
          {allRoutes.map((r) => (
            <label key={r} className="flex items-center gap-2 cursor-pointer group">
              <input
                type="checkbox"
                checked={selected.includes(r)}
                onChange={() => toggle(r)}
                className="w-3.5 h-3.5 rounded accent-indigo-500"
              />
              <span className="text-xs text-gray-300 group-hover:text-white">{r}</span>
            </label>
          ))}
        </div>
        <p className="text-xs text-gray-600 mt-1">{selected.length} route{selected.length !== 1 ? 's' : ''} selected</p>
      </Field>
    </div>
  )
}

function RouteFields({ p, set, opts }: { p: Record<string, unknown>; set: SetFn; opts: OptionsResponse }) {
  const allRoutes = [...opts.sea_routes, ...opts.arctic_routes]
  const isMultiActive = !!(p.constellation as string) || ((p.shells as ShellDef[]) ?? []).length > 0
  return (
    <div className="space-y-3">
      <SelectField label="Route" value={p.route as string} options={allRoutes} onChange={(v) => set('route', v)} />
      <div className="grid grid-cols-2 gap-3">
        <SelectField label="Comms" value={p.comms as string} options={opts.comms_payloads} onChange={(v) => set('comms', v)} />
        <SelectField label="Sat type" value={p.platform as string} options={opts.platforms} onChange={(v) => set('platform', v)} />
        <SelectField label="Weather" value={p.weather as string} options={opts.weather_scenarios} onChange={(v) => set('weather', v)} />
        <NumberField label="Duration" hint="h" value={p.duration as number} min={1} max={168} onChange={(v) => set('duration', v)} />
        <NumberField label="Speed" hint="kn" value={p.speed as number} min={1} max={50} onChange={(v) => set('speed', v)} />
        <NumberField label="Min elevation" hint="°" value={p.min_elev as number} min={0} max={90} onChange={(v) => set('min_elev', v)} />
        {isMultiActive && (
          <NumberField label="Max sats" value={(p.max_sats as number) ?? 250} min={10} max={10000} onChange={(v) => set('max_sats', v)} />
        )}
      </div>
      <div className="grid grid-cols-2 gap-x-4">
        <Toggle label="Bidirectional" value={p.bidi as boolean} onChange={(v) => set('bidi', v)} />
        <Toggle label="Trails" value={p.trails as boolean} onChange={(v) => set('trails', v)} />
      </div>
    </div>
  )
}

function buildDefaults(mode: JobMode, opts: OptionsResponse): Record<string, unknown> {
  const comms   = opts.comms_payloads[0]   ?? 'vdes'
  const weather = opts.weather_scenarios[0] ?? 'clear'
  const loc     = opts.locations[0]         ?? 'panama_canal'
  const platform = opts.platforms[0]        ?? 'smallsat'
  const route   = opts.sea_routes[0]        ?? 'north_atlantic'
  switch (mode) {
    case 'heatmap':    return { ...defaultConstellation, ...multiShellDefaults, comms, platform, weather, res: 5, min_elev: 10, bidi: false }
    case 'heatmap-rf':  return { ...defaultConstellation, ...multiShellDefaults, comms, platform, weather, res: 5, min_elev: 10, bidi: false }
    case 'sky':     return { ...defaultConstellation, ...multiShellDefaults, location: loc, coverage: false, comms, platform, weather, duration: 2, speed: 60, bidi: false, trails: false }
    case 'orbit':   return { ...defaultConstellation, ...multiShellDefaults, comms, platform, min_elev: 10, duration: 2, trails: true, map: true, beams: false, fill: false }
    case 'track':   return { ...defaultConstellation, duration: 2, map: true }
    case 'route':   return { ...defaultConstellation, ...multiShellDefaults, route, comms, platform, weather, duration: 24, speed: 12, min_elev: 10, bidi: false, trails: false }
    case 'report':  return { ...defaultConstellation, ...multiShellDefaults, comms, platform, reportRoutes: DEFAULT_REPORT_ROUTES }
  }
}

// ── Main component ─────────────────────────────────────────────────────────────

const MODES: { value: JobMode; label: string }[] = [
  { value: 'heatmap',    label: 'Heatmap' },
  { value: 'heatmap-rf', label: 'RF Heatmap' },
  { value: 'sky',        label: 'Sky' },
  { value: 'orbit',      label: 'Orbit' },
  { value: 'track',      label: 'Track' },
  { value: 'route',   label: 'Route' },
  { value: 'report',  label: '📋 Report' },
]

export default function ConfigPanel() {
  const qc     = useQueryClient()
  const { data: opts, isLoading } = useQuery({ queryKey: ['options'], queryFn: fetchOptions })

  const [mode,   setMode]   = useState<JobMode>('heatmap')
  const [params, setParams] = useState<Record<string, unknown>>(defaultConstellation)
  const [error,  setError]  = useState('')
  const [showReportConfirm, setShowReportConfirm] = useState(false)
  const [consOpen, setConsOpen] = useState(true)

  useEffect(() => {
    if (!opts) return
    setParams(buildDefaults(mode, opts))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opts])

  useEffect(() => {
    if (!opts) return
    const kept = Object.fromEntries(
      ['sats', 'planes', 'altitude', 'phasing', 'inclination', 'sso', 'backend', 'comms', 'platform'].map((k) => [k, params[k]])
    )
    setParams({ ...buildDefaults(mode, opts), ...kept })
    setError('')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode])

  const set: SetFn = (key, val) => setParams((p) => ({ ...p, [key]: val }))

  const combinedShells = (params.shells as ShellDef[]) ?? []
  const isMultiShell   = !!(params.constellation as string) || combinedShells.length > 0

  const mutation = useMutation({
    mutationFn: submitJob,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['jobs'] })
      setError('')
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail ?? 'Submission failed.'
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg))
    },
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (mode === 'report') { setShowReportConfirm(true); return }
    const submitted = { ...params }
    if (typeof submitted.duration === 'number') {
      if (mode === 'orbit')                                        submitted.duration = Math.round(submitted.duration * 60)
      else if (mode === 'sky' || mode === 'track' || mode === 'route') submitted.duration = Math.round(submitted.duration * 3600)
    }
    if (mode === 'sky' && typeof submitted.coverage === 'boolean')
      submitted.coverage = submitted.coverage ? 'all' : null
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    mutation.mutate({ mode, ...submitted } as any)
  }

  if (isLoading || !opts) {
    return <div className="p-6 text-sm text-gray-500 animate-pulse">Loading options…</div>
  }

  // Constellation state (was in ConstellationPicker, now lives here)
  const knownConstellations: Record<string, MultiShellPreset> = opts.known_constellations ?? {}
  const presetKeys    = Object.keys(knownConstellations)
  const selectedConst = (params.constellation as string) || ''
  const selectedShells = (params.shells as ShellDef[]) ?? []
  const selectedNames  = new Set(selectedShells.map((s) => s.name ?? ''))

  function toggleShell(name: string, preset: ConstellationPreset) {
    const current = (params.shells as ShellDef[]) ?? []
    if (selectedNames.has(name)) {
      const next = current.filter((s) => s.name !== name)
      set('shells', next.length > 0 ? next : null)
    } else {
      set('shells', [...current, { sats: preset.sats, planes: preset.planes, inclination: preset.inclination, altitude_km: preset.altitude, phasing: preset.phasing, name }])
      if (preset.default_comms)          set('comms',    preset.default_comms)
      if (preset.default_satellite_type) set('platform', preset.default_satellite_type)
    }
  }

  const modeLabel = MODES.find((m) => m.value === mode)?.label ?? mode

  return (
    <form onSubmit={handleSubmit} className="flex flex-col">

      {/* ── Mode tabs ─────────────────────────────────────────────────────── */}
      <div className="px-4 pt-4 pb-3 border-b border-gray-800">
        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wider mb-2">Simulation mode</p>
        <div className="flex flex-wrap gap-1.5">
          {MODES.map((m) => (
            <button
              key={m.value}
              type="button"
              onClick={() => setMode(m.value)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                mode === m.value
                  ? 'bg-indigo-600 text-white'
                  : 'text-gray-400 bg-gray-800 hover:text-white hover:bg-gray-700'
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-4 space-y-4">

        {/* ── Constellation ─────────────────────────────────────────────── */}
        <section className="rounded-xl border border-gray-800 overflow-hidden">
          <button
            type="button"
            onClick={() => setConsOpen((o) => !o)}
            className="w-full flex items-center justify-between px-3 py-2.5 bg-gray-900 hover:bg-gray-800 transition-colors"
          >
            <div className="flex items-center gap-2 min-w-0">
              <Sparkles className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" />
              <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Constellation</span>
              {isMultiShell && (
                <span className="text-xs bg-violet-900/50 text-violet-300 border border-violet-700/40 px-2 py-0.5 rounded-full font-mono leading-none truncate max-w-[120px]">
                  {params.constellation ? params.constellation as string : `${combinedShells.length} shells`}
                </span>
              )}
            </div>
            <ChevronDown className={`w-4 h-4 text-gray-500 flex-shrink-0 transition-transform duration-150 ${consOpen ? '' : '-rotate-90'}`} />
          </button>

          {consOpen && (
            <div className="px-3 pb-3 pt-2.5 space-y-3">

              {/* Named multi-shell preset */}
              {presetKeys.length > 0 && (
                <Field label="Named constellation">
                  <div className="relative">
                    <select
                      className={selectCls + ' appearance-none pr-8'}
                      value={selectedConst}
                      onChange={(e) => {
                        const name = e.target.value
                        if (name) {
                          const preset = knownConstellations[name]
                          set('constellation', name)
                          set('constellation_name', name)
                          set('shells', preset?.shells ?? null)
                          if (preset?.default_comms)          set('comms',    preset.default_comms)
                          if (preset?.default_satellite_type) set('platform', preset.default_satellite_type)
                        } else {
                          set('constellation', null)
                          set('constellation_name', null)
                          set('shells', null)
                        }
                      }}
                    >
                      <option value="">— single shell —</option>
                      {presetKeys.map((name) => (
                        <option key={name} value={name}>
                          {name} · {knownConstellations[name].description}
                        </option>
                      ))}
                    </select>
                    <Sparkles className="absolute right-2 top-2 w-4 h-4 text-violet-400 pointer-events-none" />
                  </div>
                </Field>
              )}

              {/* Single-shell area (only shown when no named multi-shell selected) */}
              {!selectedConst && (
                <>
                  {/* Combine single-shell preset checkboxes */}
                  {Object.keys(opts.constellation_presets).length > 0 && (
                    <Field label="Combine presets">
                      <div className="space-y-1.5 mt-1 max-h-28 overflow-y-auto pr-1">
                        {Object.entries(opts.constellation_presets).map(([name, preset]) => (
                          <label key={name} className="flex items-center gap-2 cursor-pointer group">
                            <input
                              type="checkbox"
                              checked={selectedNames.has(name)}
                              onChange={() => toggleShell(name, preset)}
                              className="w-3.5 h-3.5 rounded accent-indigo-500 flex-shrink-0"
                            />
                            <span className="text-xs text-gray-300 group-hover:text-white leading-tight truncate">
                              {name}
                              <span className="ml-1 text-gray-500">{preset.sats}s·{preset.altitude}km</span>
                            </span>
                          </label>
                        ))}
                      </div>
                      {selectedShells.length > 0 && (
                        <button
                          type="button"
                          className="mt-1 text-xs text-gray-500 hover:text-red-400 transition-colors"
                          onClick={() => { set('shells', null); set('constellation_name', null) }}
                        >
                          Clear {selectedShells.length} selected
                        </button>
                      )}
                    </Field>
                  )}

                  {/* Custom single-shell geometry (hidden while combined shells are active) */}
                  {!isMultiShell && (
                    <>
                      {/* Quick-fill from preset */}
                      <Field label="Quick-fill from preset">
                        <div className="relative">
                          <select
                            className={selectCls + ' appearance-none pr-8'}
                            value=""
                            onChange={(e) => {
                              const preset: ConstellationPreset | undefined = opts.constellation_presets[e.target.value]
                              if (preset) {
                                set('sats',        preset.sats)
                                set('planes',      preset.planes)
                                set('altitude',    preset.altitude)
                                set('inclination', preset.inclination)
                                set('phasing',     preset.phasing)
                                set('sso',         preset.sso)
                                if (preset.default_comms)          set('comms',    preset.default_comms)
                                if (preset.default_satellite_type) set('platform', preset.default_satellite_type)
                              }
                            }}
                          >
                            <option value="">— pick a preset —</option>
                            {Object.entries(opts.constellation_presets).map(([name, p]) => (
                              <option key={name} value={name} title={p.description}>
                                {name} ({p.sats}s · {p.altitude}km · {p.inclination}°)
                              </option>
                            ))}
                          </select>
                          <Sparkles className="absolute right-2 top-2 w-4 h-4 text-indigo-400 pointer-events-none" />
                        </div>
                      </Field>

                      {/* Geometry fields — 2-column grid */}
                      <div className="grid grid-cols-2 gap-3">
                        <NumberField label="Satellites" value={params.sats as number} min={1} max={10000} onChange={(v) => set('sats', v)} />
                        <NumberField label="Planes" value={params.planes as number} min={1} max={1000} onChange={(v) => set('planes', v)} />
                        <NumberField label="Altitude" hint="km" value={params.altitude as number} min={160} max={42000} step={10} onChange={(v) => set('altitude', v)} />
                        <NumberField label="Phasing" value={params.phasing as number} min={1} max={1000} onChange={(v) => set('phasing', v)} />
                        <div>
                          {params.sso ? (
                            <Field label="Inclination">
                              <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-gray-800/50 border border-gray-700/50 text-sm text-gray-300">
                                {(() => {
                                  const alt = params.altitude as number
                                  const mu = 398600.4418, re = 6378.137, J2 = 0.00108263
                                  const a = re + alt
                                  const n = Math.sqrt(mu / (a ** 3))
                                  const cosI = -2 * 1.99106e-7 / (3 * n * J2 * (re / a) ** 2)
                                  const inc = (Math.acos(Math.max(-1, Math.min(1, cosI))) * 180) / Math.PI
                                  return <>{inc.toFixed(1)}°</>
                                })()}
                                <span className="ml-auto text-xs text-indigo-400">SSO</span>
                              </div>
                            </Field>
                          ) : (
                            <NumberField label="Inclination" hint="°" value={params.inclination as number} min={0} max={180} step={0.1} onChange={(v) => set('inclination', v)} />
                          )}
                        </div>
                        <div className="flex items-end pb-1">
                          <Toggle label="SSO" value={params.sso as boolean} onChange={(v) => set('sso', v)} />
                        </div>
                        <div className="col-span-2">
                          <SelectField label="Backend" value={params.backend as string} options={opts.backends} onChange={(v) => set('backend', v)} />
                        </div>
                      </div>
                    </>
                  )}
                </>
              )}
            </div>
          )}
        </section>

        {/* ── Mode params ───────────────────────────────────────────────── */}
        <section className="rounded-xl border border-gray-800 overflow-hidden">
          <div className="px-3 py-2.5 bg-gray-900 border-b border-gray-800">
            <span className="text-xs font-semibold text-gray-300 uppercase tracking-wider">{modeLabel}</span>
          </div>
          <div className="px-3 py-3">
            {(mode === 'heatmap' || mode === 'heatmap-rf') && <HeatmapFields p={params} set={set} opts={opts} />}
            {mode === 'sky'     && <SkyFields        p={params} set={set} opts={opts} />}
            {mode === 'orbit'   && <OrbitFields      p={params} set={set} opts={opts} />}
            {mode === 'track'   && <TrackFields      p={params} set={set} opts={opts} />}
            {mode === 'route'   && <RouteFields      p={params} set={set} opts={opts} />}
            {mode === 'report'  && <FullReportFields p={params} set={set} opts={opts} />}
          </div>
        </section>

        {error && (
          <p className="text-xs text-red-400 bg-red-900/30 px-3 py-2 rounded-lg">{error}</p>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg
                     bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed
                     font-medium text-sm text-white transition-colors"
        >
          {mode === 'report' ? <FileText className="w-4 h-4" /> : <Play className="w-4 h-4" />}
          {mode === 'report' ? 'Generate Full Report' : mutation.isPending ? 'Submitting…' : 'Run simulation'}
        </button>
      </div>

      {showReportConfirm && opts && (
        <ReportConfirmModal
          params={params}
          opts={opts}
          onClose={() => setShowReportConfirm(false)}
        />
      )}
    </form>
  )
}
