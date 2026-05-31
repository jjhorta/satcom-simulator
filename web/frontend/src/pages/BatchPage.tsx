import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Plus, Trash2, Rocket, Satellite } from 'lucide-react'
import { submitBatchJob } from '../api/client'
import type { SweepParamDef } from '../types'

const PARAM_META: Record<string, { label: string; unit: string; isString?: boolean }> = {
  sats:        { label: 'Satellites',   unit: '' },
  planes:      { label: 'Planes',       unit: '' },
  inclination: { label: 'Inclination',  unit: '°' },
  altitude:    { label: 'Altitude',     unit: 'km' },
  phasing:     { label: 'Phasing',      unit: '' },
  weather:     { label: 'Weather',      unit: '', isString: true },
}

const COMMS_OPTIONS = ['vdes', 'ais', 'mss', 'starlink_ku', 'lte', '5g', 'gsm']
const WEATHER_OPTIONS = ['clear', 'storm', 'tropical']

function comboCount(params: SweepParamDef[]): number {
  if (params.length === 0) return 1
  return params.reduce((p, s) => p * s.values.length, 1)
}

function estTime(combos: number): string {
  const min = combos * 2
  if (min < 60) return `~${min} min`
  return `~${Math.round(min / 60)}h ${min % 60}m`
}

export default function BatchPage() {
  const navigate   = useNavigate()
  
  const [mode, setMode] = useState<'heatmap' | 'heatmap-rf' | 'coverage'>('heatmap-rf')
  const [comms, setComms] = useState('vdes')
  const [weather, setWeather] = useState('clear')
  const [resolution, setResolution] = useState(5)
  const [minElev, setMinElev] = useState(10)
  const [sweepParams, setSweepParams] = useState<SweepParamDef[]>([
    { param: 'sats', values: [12, 24, 48] },
    { param: 'inclination', values: [53, 87] },
  ])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const combos = useMemo(() => comboCount(sweepParams), [sweepParams])

  const addParam = () => {
    const available: SweepParamDef['param'][] = ['sats', 'planes', 'inclination', 'altitude', 'phasing', 'weather']
    const used = new Set(sweepParams.map(p => p.param))
    const next = available.find(a => !used.has(a))
    if (!next) return
    const defaults: Record<string, (number | string)[]> = {
      sats: [12, 24], planes: [3, 6], inclination: [53, 87],
      altitude: [550, 600], phasing: [1], weather: ['clear', 'storm'],
    }
    setSweepParams([...sweepParams, { param: next, values: defaults[next] }])
  }

  const removeParam = (idx: number) => {
    setSweepParams(sweepParams.filter((_, i) => i !== idx))
  }

  const updateValues = (idx: number, raw: string) => {
    // Check if this is a string-based param (like weather)
    const meta = PARAM_META[sweepParams[idx].param]
    if (meta?.isString) {
      const values = raw.split(/[, \t\n]+/).map(s => s.trim()).filter(s => s.length > 0)
      if (values.length === 0) return
      const updated = [...sweepParams]
      updated[idx] = { ...updated[idx], values }
      setSweepParams(updated)
      return
    }
    // Parse numeric values separated by comma, space, tab, or newline
    const values = raw.split(/[, \t\n]+/).map(s => {
      const trimmed = s.trim()
      if (trimmed === '') return NaN
      const n = parseFloat(trimmed)
      return isNaN(n) ? 0 : n
    }).filter(v => v > 0)
    if (values.length === 0) return
    const updated = [...sweepParams]
    updated[idx] = { ...updated[idx], values }
    setSweepParams(updated)
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      await submitBatchJob({
        mode,
        comms,
        weather,
        min_elev: minElev,
        res: resolution,
        fixed_params: {},
        sweep_params: sweepParams.map(sp => ({ param: sp.param, values: sp.values })),
      })
      navigate('/')
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'Failed to submit batch job'
      setError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-6">
      <div className="max-w-3xl mx-auto">
        <button onClick={() => navigate('/')}
          className="flex items-center gap-1.5 text-sm text-gray-400 hover:text-white mb-6 transition-colors">
          <ArrowLeft className="w-4 h-4" /> Back to Dashboard
        </button>

        <div className="flex items-center gap-3 mb-8">
          <Satellite className="w-6 h-6 text-indigo-400" />
          <h1 className="text-2xl font-bold">Parametric Sweep Engine</h1>
        </div>

        {/* Mode Select */}
        <div className="bg-gray-900 rounded-lg p-5 mb-4 border border-gray-800">
          <label className="text-sm text-gray-400 block mb-3">Simulation Mode</label>
          <div className="flex gap-4">
            {([
              { value: 'heatmap', label: 'Geometric (fast)', desc: 'Elevation angle only — comms ignored' },
              { value: 'heatmap-rf', label: 'RF Link Budget', desc: 'FSPL + rain + SNR margin — comms matters' },
              { value: 'coverage', label: 'Coverage (sky)', desc: 'Multi-location coverage stats' },
            ] as const).map(m => (
              <label key={m.value} className="flex items-start gap-2 cursor-pointer group">
                <input type="radio" name="mode" checked={mode === m.value} onChange={() => setMode(m.value)}
                  className="accent-indigo-500 mt-0.5" />
                <div>
                  <span className="text-sm">{m.label}</span>
                  <span className="block text-xs text-gray-500 group-hover:text-gray-400">{m.desc}</span>
                </div>
              </label>
            ))}
          </div>
        </div>

        {/* Sweep Parameters */}
        <div className="bg-gray-900 rounded-lg p-5 mb-4 border border-gray-800">
          <div className="flex items-center justify-between mb-3">
            <label className="text-sm text-gray-400">Walker Parameters to Sweep</label>
            <button onClick={addParam}
              className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
              <Plus className="w-3 h-3" /> Add Parameter
            </button>
          </div>
          {sweepParams.map((sp, i) => {
            const meta = PARAM_META[sp.param]
            return (
              <div key={sp.param} className="flex items-center gap-3 mb-2">
                <span className="w-24 text-sm text-gray-300">{meta.label}</span>
                <input
                  value={sp.values.join(', ')}
                  placeholder={meta?.isString ? 'e.g. clear, storm' : 'e.g. 12, 24, 48'}
                  onChange={(e) => updateValues(i, e.target.value)}
                  className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white
                             focus:outline-none focus:border-indigo-500"
                  placeholder="e.g. 12, 24, 48"
                />
                <span className="text-xs text-gray-500 w-8">{meta.unit}</span>
                <button onClick={() => removeParam(i)}
                  className="text-gray-500 hover:text-red-400 transition-colors">
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            )
          })}
        </div>

        {/* Fixed Parameters */}
        <div className="bg-gray-900 rounded-lg p-5 mb-4 border border-gray-800">
          <label className="text-sm text-gray-400 block mb-3">Fixed Parameters</label>
          <div className="flex flex-wrap gap-x-8 gap-y-3">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Comms</label>
              <select value={comms} onChange={e => setComms(e.target.value)}
                className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm text-white
                           focus:outline-none focus:border-indigo-500 w-36">
                {COMMS_OPTIONS.map(c => (
                  <option key={c} value={c}>{c === 'starlink_ku' ? 'Starlink Ku' : c.toUpperCase()}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Grid Resolution (°)</label>
              <input type="number" min={0.5} max={20} step={0.5} value={resolution}
                onChange={e => setResolution(parseFloat(e.target.value) || 5)}
                className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm w-24" />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">Min Elevation (°)</label>
              <input type="number" min={5} max={90} step={1} value={minElev}
                onChange={e => setMinElev(parseInt(e.target.value) || 10)}
                className="bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm w-24" />
            </div>
          </div>
          {mode !== 'heatmap-rf' && (
            <p className="text-xs text-gray-600 mt-3">💡 RF Link Budget mode uses both comms and weather in the simulation</p>
          )}
        </div>

        {/* Summary */}
        <div className="bg-gray-900 rounded-lg p-5 mb-6 border border-indigo-900/50">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-sm text-gray-400">{sweepParams.length} params &times; {combos} configurations</span>
              <span className="mx-2 text-gray-600">|</span>
              <span className="text-sm text-gray-400">Est. time: {estTime(combos)}</span>
            </div>
            <button onClick={handleSubmit} disabled={submitting || combos === 0}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-gray-700
                         disabled:text-gray-500 text-white px-5 py-2 rounded-lg transition-colors text-sm">
              <Rocket className="w-4 h-4" />
              {submitting ? 'Submitting...' : 'Start Sweep'}
            </button>
          </div>
          {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
        </div>
      </div>
    </div>
  )
}