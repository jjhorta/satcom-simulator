import { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchOptions, submitJob } from '../api/client'
import type { JobMode, OptionsResponse, ConstellationPreset } from '../types'
import { Play, ChevronDown, Sparkles } from 'lucide-react'

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

// ── Mode sections ──────────────────────────────────────────────────────────────

function HeatmapFields({ p, set, opts }: { p: Record<string, unknown>; set: SetFn; opts: OptionsResponse }) {
  return (
    <>
      <SelectField label="Comms payload" value={p.comms as string} options={opts.comms_payloads} onChange={(v) => set('comms', v)} />
      <SelectField label="Weather" value={p.weather as string} options={opts.weather_scenarios} onChange={(v) => set('weather', v)} />
      <NumberField label="Grid resolution" hint="degrees" value={p.res as number} min={0.5} max={20} step={0.5} onChange={(v) => set('res', v)} />
      <NumberField label="Min elevation" hint="degrees" value={p.min_elev as number} min={0} max={90} onChange={(v) => set('min_elev', v)} />
      <Toggle label="Bidirectional" value={p.bidi as boolean} onChange={(v) => set('bidi', v)} />
    </>
  )
}

function SkyFields({ p, set, opts }: { p: Record<string, unknown>; set: SetFn; opts: OptionsResponse }) {
  return (
    <>
      <SelectField label="Location" value={p.location as string} options={opts.locations} onChange={(v) => set('location', v)} />
      <Toggle label="Coverage pass" value={p.coverage as boolean} onChange={(v) => set('coverage', v)} />
      <SelectField label="Comms payload" value={p.comms as string} options={opts.comms_payloads} onChange={(v) => set('comms', v)} />
      <SelectField label="Weather" value={p.weather as string} options={opts.weather_scenarios} onChange={(v) => set('weather', v)} />
      <NumberField label="Duration" hint="hours" value={p.duration as number} min={1} max={168} onChange={(v) => set('duration', v)} />
      <NumberField label="Speed" hint="×" value={p.speed as number} min={1} max={3600} onChange={(v) => set('speed', v)} />
      <Toggle label="Bidirectional" value={p.bidi as boolean} onChange={(v) => set('bidi', v)} />
      <Toggle label="Trails" value={p.trails as boolean} onChange={(v) => set('trails', v)} />
    </>
  )
}

function OrbitFields({ p, set, opts }: { p: Record<string, unknown>; set: SetFn; opts: OptionsResponse }) {
  return (
    <>
      <SelectField label="Comms payload" value={p.comms as string} options={opts.comms_payloads} onChange={(v) => set('comms', v)} />
      <SelectField label="Platform" value={p.platform as string} options={opts.platforms} onChange={(v) => set('platform', v)} />
      <NumberField label="Min elevation" hint="degrees" value={p.min_elev as number} min={0} max={90} onChange={(v) => set('min_elev', v)} />
      <NumberField label="Duration" hint="hours" value={p.duration as number} min={1} max={168} onChange={(v) => set('duration', v)} />
      <Toggle label="Trails" value={p.trails as boolean} onChange={(v) => set('trails', v)} />
      <Toggle label="Map" value={p.map as boolean} onChange={(v) => set('map', v)} />
      <Toggle label="Beam footprints" value={p.beams as boolean} onChange={(v) => set('beams', v)} />
    </>
  )
}

function TrackFields({ p, set }: { p: Record<string, unknown>; set: SetFn; opts: OptionsResponse }) {
  return (
    <>
      <NumberField label="Duration" hint="hours" value={p.duration as number} min={1} max={168} onChange={(v) => set('duration', v)} />
      <Toggle label="Map" value={p.map as boolean} onChange={(v) => set('map', v)} />
    </>
  )
}

function RouteFields({ p, set, opts }: { p: Record<string, unknown>; set: SetFn; opts: OptionsResponse }) {
  const allRoutes = [...opts.sea_routes, ...opts.arctic_routes]
  return (
    <>
      <SelectField label="Route" value={p.route as string} options={allRoutes} onChange={(v) => set('route', v)} />
      <SelectField label="Comms payload" value={p.comms as string} options={opts.comms_payloads} onChange={(v) => set('comms', v)} />
      <SelectField label="Weather" value={p.weather as string} options={opts.weather_scenarios} onChange={(v) => set('weather', v)} />
      <NumberField label="Duration" hint="hours" value={p.duration as number} min={1} max={168} onChange={(v) => set('duration', v)} />
      <NumberField label="Speed" hint="knots" value={p.speed as number} min={1} max={50} onChange={(v) => set('speed', v)} />
      <NumberField label="Min elevation" hint="degrees" value={p.min_elev as number} min={0} max={90} onChange={(v) => set('min_elev', v)} />
      <Toggle label="Bidirectional" value={p.bidi as boolean} onChange={(v) => set('bidi', v)} />
      <Toggle label="Trails" value={p.trails as boolean} onChange={(v) => set('trails', v)} />
    </>
  )
}

type SetFn = (key: string, val: unknown) => void

function buildDefaults(mode: JobMode, opts: OptionsResponse): Record<string, unknown> {
  const comms   = opts.comms_payloads[0]   ?? 'vdes'
  const weather = opts.weather_scenarios[0] ?? 'clear'
  const loc     = opts.locations[0]         ?? 'panama_canal'
  const platform = opts.platforms[0]        ?? 'smallsat'
  const route   = opts.sea_routes[0]        ?? 'north_atlantic'
  switch (mode) {
    case 'heatmap': return { ...defaultConstellation, comms, weather, res: 5, min_elev: 10, bidi: false }
    case 'sky':     return { ...defaultConstellation, location: loc, coverage: false, comms, weather, duration: 2, speed: 60, bidi: false, trails: false }
    case 'orbit':   return { ...defaultConstellation, comms, platform, min_elev: 10, duration: 2, trails: true, map: true, beams: false }
    case 'track':   return { ...defaultConstellation, duration: 2, map: true }
    case 'route':   return { ...defaultConstellation, route, comms, weather, duration: 24, speed: 12, min_elev: 10, bidi: false, trails: false }
  }
}

// ── Main component ─────────────────────────────────────────────────────────────

const MODES: { value: JobMode; label: string }[] = [
  { value: 'heatmap', label: 'Coverage Heatmap' },
  { value: 'sky',     label: 'Sky / Coverage Pass' },
  { value: 'orbit',   label: 'Orbit Animation' },
  { value: 'track',   label: 'Ground Track' },
  { value: 'route',   label: 'Maritime Route' },
]

export default function ConfigPanel() {
  const qc     = useQueryClient()
  const { data: opts, isLoading } = useQuery({ queryKey: ['options'], queryFn: fetchOptions })

  const [mode,   setMode]   = useState<JobMode>('heatmap')
  const [params, setParams] = useState<Record<string, unknown>>(defaultConstellation)
  const [error,  setError]  = useState('')

  // Once options load, seed params with real first values
  useEffect(() => {
    if (!opts) return
    setParams(buildDefaults(mode, opts))
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [opts])

  // Reset mode-specific params but keep constellation geometry when switching mode
  useEffect(() => {
    if (!opts) return
    const constellationKeys = ['sats', 'planes', 'altitude', 'phasing', 'inclination', 'sso', 'backend']
    const kept = Object.fromEntries(
      constellationKeys.map((k) => [k, params[k]])
    )
    setParams({ ...buildDefaults(mode, opts), ...kept })
    setError('')
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode])

  const set: SetFn = (key, val) => setParams((p) => ({ ...p, [key]: val }))

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
    // Convert duration from hours (UI) to the unit the API expects
    const submitted = { ...params }
    if (typeof submitted.duration === 'number') {
      if (mode === 'orbit') {
        submitted.duration = Math.round(submitted.duration * 60)          // hours → minutes
      } else if (mode === 'sky' || mode === 'track' || mode === 'route') {
        submitted.duration = Math.round(submitted.duration * 3600)        // hours → seconds
      }
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    mutation.mutate({ mode, ...submitted } as any)
  }

  if (isLoading || !opts) {
    return (
      <div className="p-6 text-sm text-gray-500 animate-pulse">Loading options…</div>
    )
  }

  const modeFieldProps = { p: params, set, opts }

  return (
    <form onSubmit={handleSubmit} className="p-4 space-y-5">
      <h2 className="text-sm font-semibold text-gray-200 uppercase tracking-wider">
        New Simulation
      </h2>

      {/* Mode selector */}
      <Field label="Mode">
        <div className="relative">
          <select
            className={selectCls + ' appearance-none pr-8'}
            value={mode}
            onChange={(e) => setMode(e.target.value as JobMode)}
          >
            {MODES.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
          </select>
          <ChevronDown className="absolute right-2 top-2 w-4 h-4 text-gray-500 pointer-events-none" />
        </div>
      </Field>

      {/* ── Constellation geometry ──────────────────────────────────────────── */}
      <section>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
          Constellation
        </p>
        <div className="space-y-3">
          {/* Preset picker */}
          <Field label="Preset constellation">
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
                  }
                }}
              >
                <option value="">— pick a preset —</option>
                {Object.entries(opts.constellation_presets).map(([name, p]) => (
                  <option key={name} value={name} title={p.description}>
                    {name} ({p.sats} sats · {p.altitude} km · {p.inclination}°)
                  </option>
                ))}
              </select>
              <Sparkles className="absolute right-2 top-2 w-4 h-4 text-indigo-400 pointer-events-none" />
            </div>
          </Field>
          <NumberField label="Satellites" value={params.sats as number} min={1} max={10000} onChange={(v) => set('sats', v)} />
          <NumberField label="Planes" value={params.planes as number} min={1} max={1000} onChange={(v) => set('planes', v)} />
          <NumberField label="Altitude" hint="km" value={params.altitude as number} min={160} max={42000} step={10} onChange={(v) => set('altitude', v)} />
          <NumberField label="Phasing" value={params.phasing as number} min={1} max={1000} onChange={(v) => set('phasing', v)} />
          <div className="flex items-center gap-3">
            <div className="flex-1">
              <NumberField label="Inclination" hint="deg" value={params.inclination as number} min={0} max={180} step={0.1} onChange={(v) => set('inclination', v)} />
            </div>
            <div className="pt-5">
              <Toggle label="SSO" value={params.sso as boolean} onChange={(v) => set('sso', v)} />
            </div>
          </div>
          <SelectField label="Backend" value={params.backend as string} options={opts.backends} onChange={(v) => set('backend', v)} />
        </div>
      </section>

      {/* ── Mode-specific params ────────────────────────────────────────────── */}
      <section>
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wider mb-3">
          {MODES.find((m) => m.value === mode)?.label}
        </p>
        <div className="space-y-3">
          {mode === 'heatmap' && <HeatmapFields {...modeFieldProps} />}
          {mode === 'sky'     && <SkyFields     {...modeFieldProps} />}
          {mode === 'orbit'   && <OrbitFields   {...modeFieldProps} />}
          {mode === 'track'   && <TrackFields   {...modeFieldProps} />}
          {mode === 'route'   && <RouteFields   {...modeFieldProps} />}
        </div>
      </section>

      {error && (
        <p className="text-xs text-red-400 bg-red-900/30 px-3 py-2 rounded-lg">{error}</p>
      )}

      <button
        type="submit"
        disabled={mutation.isPending}
        className="w-full flex items-center justify-center gap-2 py-2 px-4 rounded-lg
                   bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed
                   font-medium text-sm text-white transition-colors"
      >
        <Play className="w-4 h-4" />
        {mutation.isPending ? 'Submitting…' : 'Run simulation'}
      </button>
    </form>
  )
}
