import { useQuery } from '@tanstack/react-query'
import { fetchCsv, fileUrl } from '../../api/client'
import { Download, Radio, Activity, Zap } from 'lucide-react'

// ── Types ────────────────────────────────────────────────────────────────────
interface LatencyRow {
  time_min:      number
  rtt_ms:        number
  one_way_ms:    number
  num_hops:      number
  src_visible:   number
  dst_visible:   number
  path_found:    number
  uplink_ms:     number
  downlink_ms:   number
  isl_ms:        number
  switching_ms:  number
}

interface LatencyHop {
  type:     string
  from:     string
  to:       string
  dist_km:  number
  delay_ms: number
}

interface LatencySummary {
  source:      { lat: number; lon: number; raw: string }
  destination: { lat: number; lon: number; raw: string }
  constellation_suffix: string
  snapshots:           number
  step_min:            number
  duration_min:        number
  isl_range_km:        number
  switching_delay_ms:  number
  min_elev_deg:        number
  availability_pct:    number
  rtt: {
    min_ms:    number
    p5_ms:     number
    median_ms: number
    mean_ms:   number
    p95_ms:    number
    max_ms:    number
    std_ms:    number
  }
  fiber: null | {
    great_circle_km: number
    one_way_ms:      number
    rtt_ms:          number
    pct_below_fiber: number | null
  }
  representative_path: null | {
    total_one_way_ms: number
    total_rtt_ms:     number
    num_hops:         number
    uplink_ms:        number
    downlink_ms:      number
    isl_ms:           number
    switching_ms:     number
    hops:             LatencyHop[]
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────
function fmt(n: number | null | undefined, digits = 2): string {
  if (n === null || n === undefined || Number.isNaN(n)) return '—'
  return n.toFixed(digits)
}

// ── Inline SVG charts ────────────────────────────────────────────────────────
function TimeSeriesChart({ rows, fiberRtt }: { rows: LatencyRow[]; fiberRtt: number | null }) {
  if (!rows.length) return null
  const W = 720, H = 220, PAD = 36
  const xs = rows.map((r) => r.time_min)
  const ys = rows.map((r) => (r.path_found ? r.rtt_ms : NaN))
  const valid = ys.filter((v) => !Number.isNaN(v))
  const yMin = Math.min(...valid, fiberRtt ?? Infinity) * 0.95
  const yMax = Math.max(...valid, fiberRtt ?? -Infinity) * 1.05
  const xMin = Math.min(...xs), xMax = Math.max(...xs)
  const sx = (x: number) => PAD + ((x - xMin) / (xMax - xMin || 1)) * (W - 2 * PAD)
  const sy = (y: number) => H - PAD - ((y - yMin) / (yMax - yMin || 1)) * (H - 2 * PAD)
  const path = rows
    .map((r, i) => {
      if (!r.path_found) return null
      const cmd = i === 0 || !rows[i - 1].path_found ? 'M' : 'L'
      return `${cmd}${sx(r.time_min).toFixed(1)},${sy(r.rtt_ms).toFixed(1)}`
    })
    .filter(Boolean)
    .join(' ')
  const fiberY = fiberRtt !== null ? sy(fiberRtt) : null

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 240 }}>
      {/* axes */}
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#374151" />
      <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="#374151" />
      {/* y ticks */}
      {[0, 0.25, 0.5, 0.75, 1].map((t) => {
        const v = yMin + t * (yMax - yMin)
        const y = sy(v)
        return (
          <g key={t}>
            <line x1={PAD - 4} y1={y} x2={W - PAD} y2={y} stroke="#1f2937" strokeDasharray="2 3" />
            <text x={PAD - 6} y={y + 3} fill="#9ca3af" fontSize="10" textAnchor="end">{v.toFixed(1)}</text>
          </g>
        )
      })}
      {/* fiber baseline */}
      {fiberY !== null && (
        <>
          <line x1={PAD} y1={fiberY} x2={W - PAD} y2={fiberY} stroke="#f59e0b" strokeDasharray="4 4" />
          <text x={W - PAD - 4} y={fiberY - 4} fill="#f59e0b" fontSize="10" textAnchor="end">fiber {fmt(fiberRtt!, 1)} ms</text>
        </>
      )}
      {/* line */}
      <path d={path} fill="none" stroke="#22d3ee" strokeWidth="1.5" />
      {/* labels */}
      <text x={W / 2} y={H - 6} fill="#6b7280" fontSize="10" textAnchor="middle">time (min)</text>
      <text x={10} y={H / 2} fill="#6b7280" fontSize="10" transform={`rotate(-90 10 ${H / 2})`} textAnchor="middle">RTT (ms)</text>
    </svg>
  )
}

function HistogramChart({ values }: { values: number[] }) {
  if (!values.length) return null
  const W = 360, H = 180, PAD = 30
  const bins = 24
  const lo = Math.min(...values), hi = Math.max(...values)
  const step = (hi - lo) / bins || 1
  const counts = new Array(bins).fill(0)
  values.forEach((v) => {
    const i = Math.min(bins - 1, Math.max(0, Math.floor((v - lo) / step)))
    counts[i] += 1
  })
  const maxC = Math.max(...counts)
  const bw = (W - 2 * PAD) / bins
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 200 }}>
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#374151" />
      {counts.map((c, i) => {
        const h = (c / maxC) * (H - 2 * PAD)
        return <rect key={i} x={PAD + i * bw + 1} y={H - PAD - h} width={bw - 1} height={h} fill="#22d3ee" opacity="0.7" />
      })}
      <text x={W / 2} y={H - 6} fill="#6b7280" fontSize="10" textAnchor="middle">RTT (ms)</text>
      <text x={PAD} y={H - PAD + 12} fill="#9ca3af" fontSize="9" textAnchor="start">{lo.toFixed(1)}</text>
      <text x={W - PAD} y={H - PAD + 12} fill="#9ca3af" fontSize="9" textAnchor="end">{hi.toFixed(1)}</text>
    </svg>
  )
}

function CdfChart({ values, fiberRtt }: { values: number[]; fiberRtt: number | null }) {
  if (!values.length) return null
  const W = 360, H = 180, PAD = 30
  const sorted = [...values].sort((a, b) => a - b)
  const lo = sorted[0], hi = sorted[sorted.length - 1]
  const sx = (x: number) => PAD + ((x - lo) / (hi - lo || 1)) * (W - 2 * PAD)
  const sy = (p: number) => H - PAD - p * (H - 2 * PAD)
  const path = sorted.map((v, i) => `${i === 0 ? 'M' : 'L'}${sx(v).toFixed(1)},${sy((i + 1) / sorted.length).toFixed(1)}`).join(' ')
  const fx = fiberRtt !== null ? sx(Math.max(lo, Math.min(hi, fiberRtt))) : null
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ maxHeight: 200 }}>
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#374151" />
      <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="#374151" />
      {[0, 0.25, 0.5, 0.75, 1].map((p) => (
        <g key={p}>
          <line x1={PAD} y1={sy(p)} x2={W - PAD} y2={sy(p)} stroke="#1f2937" strokeDasharray="2 3" />
          <text x={PAD - 4} y={sy(p) + 3} fill="#9ca3af" fontSize="9" textAnchor="end">{(p * 100).toFixed(0)}%</text>
        </g>
      ))}
      {fx !== null && (
        <line x1={fx} y1={PAD} x2={fx} y2={H - PAD} stroke="#f59e0b" strokeDasharray="3 3" />
      )}
      <path d={path} fill="none" stroke="#a78bfa" strokeWidth="1.8" />
      <text x={W / 2} y={H - 6} fill="#6b7280" fontSize="10" textAnchor="middle">RTT (ms)</text>
    </svg>
  )
}

// ── Main viewer ──────────────────────────────────────────────────────────────
export default function LatencyViewer({
  jobId, csvFilename, jsonFilename,
}: { jobId: string; csvFilename: string; jsonFilename: string }) {
  const { data: rows = [], isLoading: csvLoading, isError: csvError } = useQuery<LatencyRow[]>({
    queryKey: ['csv', jobId, csvFilename],
    queryFn:  () => (fetchCsv(jobId, csvFilename) as unknown) as Promise<LatencyRow[]>,
  })

  const { data: summary, isLoading: jsonLoading, isError: jsonError } = useQuery<LatencySummary>({
    queryKey: ['latency-json', jobId, jsonFilename],
    queryFn: () => fetch(fileUrl(jobId, jsonFilename)).then((r) => {
      if (!r.ok) throw new Error('Failed to load summary')
      return r.json()
    }),
  })

  if (csvLoading || jsonLoading) return <p className="text-sm text-gray-500 animate-pulse">Loading latency…</p>
  if (csvError || jsonError || !summary) return <p className="text-sm text-red-400">Failed to load latency data.</p>

  // Coerce numeric strings (CSV parser yields strings)
  const numRows: LatencyRow[] = rows.map((r) => ({
    time_min:     +r.time_min,
    rtt_ms:       +r.rtt_ms,
    one_way_ms:   +r.one_way_ms,
    num_hops:     +r.num_hops,
    src_visible:  +r.src_visible,
    dst_visible:  +r.dst_visible,
    path_found:   +r.path_found,
    uplink_ms:    +r.uplink_ms,
    downlink_ms:  +r.downlink_ms,
    isl_ms:       +r.isl_ms,
    switching_ms: +r.switching_ms,
  }))

  const rttValues = numRows.filter((r) => r.path_found).map((r) => r.rtt_ms)
  const fiberRtt = summary.fiber?.rtt_ms ?? null
  const pctBelow = summary.fiber?.pct_below_fiber ?? null

  const csvUrl = fileUrl(jobId, csvFilename)
  const jsonUrl = fileUrl(jobId, jsonFilename)

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm">
          <Radio className="w-4 h-4 text-cyan-400" />
          <span className="text-gray-300 font-mono">{summary.source.raw}</span>
          <span className="text-gray-600">→</span>
          <span className="text-gray-300 font-mono">{summary.destination.raw}</span>
          <span className="text-gray-600">·</span>
          <span className="text-gray-500">{summary.snapshots} snapshots ({summary.duration_min} min, step {summary.step_min} min)</span>
        </div>
        <div className="flex gap-2">
          <a href={csvUrl} download className="flex items-center gap-1 text-xs text-gray-500 hover:text-cyan-400">
            <Download className="w-3 h-3" /> CSV
          </a>
          <a href={jsonUrl} download className="flex items-center gap-1 text-xs text-gray-500 hover:text-cyan-400">
            <Download className="w-3 h-3" /> JSON
          </a>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
        <StatCard label="Min RTT"     value={`${fmt(summary.rtt.min_ms)} ms`} />
        <StatCard label="P5 RTT"      value={`${fmt(summary.rtt.p5_ms)} ms`} />
        <StatCard label="Median (P50)" value={`${fmt(summary.rtt.median_ms)} ms`} accent />
        <StatCard label="Mean"        value={`${fmt(summary.rtt.mean_ms)} ms`} />
        <StatCard label="P95"         value={`${fmt(summary.rtt.p95_ms)} ms`} />
        <StatCard label="Max"         value={`${fmt(summary.rtt.max_ms)} ms`} />
        <StatCard label="Std. dev."   value={`${fmt(summary.rtt.std_ms)} ms`} />
        <StatCard label="Availability" value={`${fmt(summary.availability_pct, 1)}%`} accent />
      </div>

      {/* Fiber comparison */}
      {summary.fiber && (
        <div className="bg-amber-950/30 border border-amber-800/40 rounded-lg p-3 flex flex-wrap items-center gap-x-6 gap-y-1 text-xs">
          <Zap className="w-4 h-4 text-amber-400" />
          <span className="text-amber-200 font-medium">Fiber baseline</span>
          <span className="text-gray-400">Great-circle <span className="text-gray-200 font-mono">{summary.fiber.great_circle_km.toFixed(0)} km</span></span>
          <span className="text-gray-400">RTT <span className="text-gray-200 font-mono">{fmt(summary.fiber.rtt_ms, 2)} ms</span></span>
          {pctBelow !== null && (
            <span className="text-gray-400">Satellite RTT &lt; fiber <span className={`font-mono ${pctBelow >= 50 ? 'text-emerald-300' : 'text-amber-300'}`}>{fmt(pctBelow, 1)}%</span> of the time</span>
          )}
        </div>
      )}

      {/* Time-series */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-3">
        <p className="text-xs text-gray-400 mb-2 flex items-center gap-1">
          <Activity className="w-3 h-3" /> RTT over time
        </p>
        <TimeSeriesChart rows={numRows} fiberRtt={fiberRtt} />
      </div>

      {/* Histogram + CDF */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-3">
          <p className="text-xs text-gray-400 mb-2">RTT histogram</p>
          <HistogramChart values={rttValues} />
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-3">
          <p className="text-xs text-gray-400 mb-2">RTT CDF {fiberRtt !== null && <span className="text-amber-400">· fiber dashed</span>}</p>
          <CdfChart values={rttValues} fiberRtt={fiberRtt} />
        </div>
      </div>

      {/* Representative path breakdown */}
      {summary.representative_path && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-3 text-xs">
          <p className="text-gray-400 mb-2">Representative path (median snapshot)</p>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
            <StatCard label="Hops"        value={`${summary.representative_path.num_hops}`} />
            <StatCard label="Uplink"      value={`${fmt(summary.representative_path.uplink_ms)} ms`} />
            <StatCard label="ISL"         value={`${fmt(summary.representative_path.isl_ms)} ms`} />
            <StatCard label="Downlink"    value={`${fmt(summary.representative_path.downlink_ms)} ms`} />
            <StatCard label="Switching"   value={`${fmt(summary.representative_path.switching_ms)} ms`} />
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="text-gray-500">
                <tr className="border-b border-gray-800">
                  <th className="text-left px-2 py-1">#</th>
                  <th className="text-left px-2 py-1">Type</th>
                  <th className="text-left px-2 py-1">From</th>
                  <th className="text-left px-2 py-1">To</th>
                  <th className="text-right px-2 py-1">Dist (km)</th>
                  <th className="text-right px-2 py-1">Delay (ms)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {summary.representative_path.hops.map((h, i) => (
                  <tr key={i}>
                    <td className="px-2 py-1 text-gray-500">{i + 1}</td>
                    <td className="px-2 py-1 font-mono text-cyan-400">{h.type}</td>
                    <td className="px-2 py-1 font-mono text-gray-300">{h.from}</td>
                    <td className="px-2 py-1 font-mono text-gray-300">{h.to}</td>
                    <td className="px-2 py-1 text-right tabular-nums text-gray-400">{h.dist_km.toFixed(1)}</td>
                    <td className="px-2 py-1 text-right tabular-nums text-gray-300">{h.delay_ms.toFixed(3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className={`rounded-lg border px-3 py-2 ${accent ? 'border-cyan-700/50 bg-cyan-950/30' : 'border-gray-800 bg-gray-900'}`}>
      <p className="text-[10px] uppercase tracking-wider text-gray-500">{label}</p>
      <p className={`text-sm font-mono ${accent ? 'text-cyan-200' : 'text-gray-200'}`}>{value}</p>
    </div>
  )
}
