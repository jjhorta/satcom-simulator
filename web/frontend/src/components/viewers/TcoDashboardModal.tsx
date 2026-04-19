import { useQuery } from '@tanstack/react-query'
import { fetchTco } from '../../api/client'
import { X } from 'lucide-react'

// ── Types ──────────────────────────────────────────────────────────────────────
interface TcoData {
  mission_parameters: {
    num_satellites:        number
    num_planes:            number
    platform_description:  string
    satellite_mass_kg:     number
    payload_type:          string
    satellite_lifetime_years: number
    replacement_rate_per_year: number
    mission_duration_years: number
  }
  launch_config: {
    launch_vehicle_description: string
    batch_size:         number
    initial_launches:   number
    annual_replacement_launches: number
  }
  capex: {
    development:           number
    initial_satellites:    number
    initial_launches:      number
    ground_infrastructure: number
    launch_insurance:      number
    total:                 number
  }
  annual_opex: {
    satellite_replacement: number
    replacement_launches:  number
    ground_operations:     number
    staff:                 number
    insurance:             number
    decommissioning:       number
    total:                 number
  }
  total_costs: {
    total_capex:          number
    total_opex:           number
    total_tco:            number
    cost_per_sat_per_year: number
  }
  infrastructure: {
    ground_stations: number
    engineers:       number
  }
  orbital: {
    period_min:      number
    velocity_km_s:   number
    orbits_per_day:  number
  }
  coverage: {
    min_elevation_deg:    number
    radius_km:            number
    area_km2:             number
    coverage_per_sat_pct: number
    avg_revisit_time_min: number
    max_gap_time_min:     number
  }
  constellation: {
    total_satellites: number
    num_planes:       number
    sats_per_plane:   number
    altitude_km:      number
    inclination_deg:  number
  }
  lifetime: {
    satellite_lifetime_years:   number
    replacement_rate_per_year:  number
    initial_launches:           number
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function fmt(v: number, decimals = 1) {
  return v.toFixed(decimals)
}
function fmtM(v: number) {
  return `$${v.toFixed(1)}M`
}

// ── KPI Card ───────────────────────────────────────────────────────────────────
function KpiCard({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="bg-gray-800/60 border border-gray-700/50 rounded-xl p-4 flex flex-col gap-1">
      <span className="text-xs text-gray-500 uppercase tracking-wider">{label}</span>
      <span className="text-2xl font-bold text-white leading-tight">{value}</span>
      {sub && <span className="text-xs text-gray-500">{sub}</span>}
    </div>
  )
}

// ── SVG Donut Chart ────────────────────────────────────────────────────────────
const DONUT_COLORS = ['#6366f1', '#06b6d4', '#f59e0b', '#10b981', '#f43f5e']

function DonutChart({ slices }: { slices: { label: string; value: number }[] }) {
  const total = slices.reduce((s, x) => s + x.value, 0)
  if (total === 0) return null

  const R = 70, r = 42, cx = 90, cy = 90
  let cumAngle = -Math.PI / 2

  const paths = slices.map((slice, i) => {
    const angle = (slice.value / total) * 2 * Math.PI
    const x1 = cx + R * Math.cos(cumAngle)
    const y1 = cy + R * Math.sin(cumAngle)
    cumAngle += angle
    const x2 = cx + R * Math.cos(cumAngle)
    const y2 = cy + R * Math.sin(cumAngle)
    const largeArc = angle > Math.PI ? 1 : 0

    const ix1 = cx + r * Math.cos(cumAngle - angle)
    const iy1 = cy + r * Math.sin(cumAngle - angle)
    const ix2 = cx + r * Math.cos(cumAngle)
    const iy2 = cy + r * Math.sin(cumAngle)

    const d = [
      `M ${x1} ${y1}`,
      `A ${R} ${R} 0 ${largeArc} 1 ${x2} ${y2}`,
      `L ${ix2} ${iy2}`,
      `A ${r} ${r} 0 ${largeArc} 0 ${ix1} ${iy1}`,
      'Z',
    ].join(' ')

    return <path key={i} d={d} fill={DONUT_COLORS[i % DONUT_COLORS.length]} opacity={0.9} />
  })

  return (
    <svg viewBox="0 0 180 180" className="w-36 h-36 flex-shrink-0">
      {paths}
      <text x={cx} y={cy - 6} textAnchor="middle" fill="#e5e7eb" fontSize={10}>CAPEX</text>
      <text x={cx} y={cy + 8} textAnchor="middle" fill="#e5e7eb" fontSize={10}>breakdown</text>
    </svg>
  )
}

// ── SVG Horizontal Bar Chart ───────────────────────────────────────────────────
function BarChart({ items }: { items: { label: string; value: number; color: string }[] }) {
  const max = Math.max(...items.map((i) => i.value), 1)
  return (
    <div className="space-y-2 w-full">
      {items.map((item, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span className="text-gray-400 w-40 truncate flex-shrink-0">{item.label}</span>
          <div className="flex-1 bg-gray-800 rounded-full h-3 overflow-hidden">
            <div
              className="h-3 rounded-full transition-all"
              style={{ width: `${(item.value / max) * 100}%`, background: item.color }}
            />
          </div>
          <span className="text-gray-300 w-16 text-right tabular-nums flex-shrink-0">
            {fmtM(item.value)}/yr
          </span>
        </div>
      ))}
    </div>
  )
}

// ── SVG Cumulative Cost Line Chart ─────────────────────────────────────────────
function CumulativeCostChart({ capex, annualOpex, years }: { capex: number; annualOpex: number; years: number }) {
  const W = 400, H = 160, padL = 50, padB = 28, padR = 16, padT = 10
  const plotW = W - padL - padR
  const plotH = H - padT - padB

  const pts = Array.from({ length: years + 1 }, (_, y) => capex + annualOpex * y)
  const maxVal = pts[pts.length - 1]

  const toX = (y: number) => padL + (y / years) * plotW
  const toY = (v: number) => padT + plotH - (v / maxVal) * plotH

  const linePath = pts.map((v, i) => `${i === 0 ? 'M' : 'L'} ${toX(i)} ${toY(v)}`).join(' ')
  const areaPath = [
    `M ${toX(0)} ${toY(0)}`,
    ...pts.map((v, i) => `L ${toX(i)} ${toY(v)}`),
    `L ${toX(years)} ${toY(0)}`,
    'Z',
  ].join(' ')

  // Y-axis labels: 0, mid, max
  const yLabels = [0, maxVal / 2, maxVal]
  // X-axis labels: 0, mid, end year
  const xLabels = [0, Math.round(years / 2), years]

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: 160 }}>
      <defs>
        <linearGradient id="areafill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#6366f1" stopOpacity={0.4} />
          <stop offset="100%" stopColor="#6366f1" stopOpacity={0.05} />
        </linearGradient>
      </defs>
      {/* Grid lines */}
      {yLabels.map((v, i) => (
        <line key={i} x1={padL} y1={toY(v)} x2={W - padR} y2={toY(v)}
          stroke="#374151" strokeWidth={0.5} strokeDasharray="4 3" />
      ))}
      {/* Area fill */}
      <path d={areaPath} fill="url(#areafill)" />
      {/* Line */}
      <path d={linePath} fill="none" stroke="#6366f1" strokeWidth={2} strokeLinejoin="round" />
      {/* Y-axis labels */}
      {yLabels.map((v, i) => (
        <text key={i} x={padL - 4} y={toY(v) + 4} textAnchor="end"
          fill="#6b7280" fontSize={8}>
          ${(v / 1000).toFixed(0)}B
        </text>
      ))}
      {/* X-axis labels */}
      {xLabels.map((y, i) => (
        <text key={i} x={toX(y)} y={H - 4} textAnchor="middle"
          fill="#6b7280" fontSize={8}>
          Y{y}
        </text>
      ))}
      {/* Axes */}
      <line x1={padL} y1={padT} x2={padL} y2={H - padB} stroke="#4b5563" strokeWidth={1} />
      <line x1={padL} y1={H - padB} x2={W - padR} y2={H - padB} stroke="#4b5563" strokeWidth={1} />
    </svg>
  )
}

// ── Legend row ────────────────────────────────────────────────────────────────
function Legend({ items }: { items: { label: string; value: number; color: string }[] }) {
  const total = items.reduce((s, i) => s + i.value, 0)
  return (
    <div className="space-y-1">
      {items.map((item, i) => (
        <div key={i} className="flex items-center gap-2 text-xs">
          <span className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: item.color }} />
          <span className="text-gray-400 flex-1">{item.label}</span>
          <span className="text-gray-300 tabular-nums">{fmtM(item.value)}</span>
          <span className="text-gray-600 tabular-nums w-10 text-right">
            {total > 0 ? `${((item.value / total) * 100).toFixed(0)}%` : '–'}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Section heading ───────────────────────────────────────────────────────────
function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold text-indigo-400 uppercase tracking-widest mb-3">
      {children}
    </h3>
  )
}

// ── Main modal ────────────────────────────────────────────────────────────────
export default function TcoDashboardModal({ jobId, onClose }: { jobId: string; onClose: () => void }) {
  const { data, isLoading, isError } = useQuery<TcoData>({
    queryKey: ['tco', jobId],
    queryFn:  () => fetchTco(jobId),
  })

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl w-full max-w-5xl max-h-[92vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <div>
            <h2 className="text-base font-semibold text-white">Business Plan Dashboard</h2>
            <p className="text-xs text-gray-500 mt-0.5">Total Cost of Ownership · Executive Overview</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 p-6 space-y-8">
          {isLoading && (
            <p className="text-sm text-gray-500 animate-pulse text-center py-16">Loading business plan…</p>
          )}
          {isError && (
            <p className="text-sm text-red-400 text-center py-16">
              No TCO data available. Re-run the orbit simulation to generate it.
            </p>
          )}

          {data && (() => {
            const mp   = data.mission_parameters
            const capex = data.capex
            const opex  = data.annual_opex
            const tc    = data.total_costs
            const con   = data.constellation
            const orb   = data.orbital
            const cov   = data.coverage
            const infra = data.infrastructure

            const capexSlices = [
              { label: 'Development',       value: capex.development },
              { label: 'Satellites',        value: capex.initial_satellites },
              { label: 'Launches',          value: capex.initial_launches },
              { label: 'Ground Infra',      value: capex.ground_infrastructure },
              { label: 'Insurance',         value: capex.launch_insurance },
            ]

            const opexBars = [
              { label: 'Sat Replacement',   value: opex.satellite_replacement, color: '#6366f1' },
              { label: 'Repl. Launches',    value: opex.replacement_launches,  color: '#06b6d4' },
              { label: 'Ground Ops',        value: opex.ground_operations,     color: '#f59e0b' },
              { label: 'Staff',             value: opex.staff,                 color: '#10b981' },
              { label: 'In-Orbit Insurance',value: opex.insurance,             color: '#f43f5e' },
              { label: 'Decommissioning',   value: opex.decommissioning,       color: '#a78bfa' },
            ]

            return (
              <>
                {/* ── KPIs ─────────────────────────────────────────────────── */}
                <section>
                  <SectionTitle>Mission at a glance</SectionTitle>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    <KpiCard label="Total TCO" value={fmtM(tc.total_tco)}
                      sub={`over ${mp.mission_duration_years} years`} />
                    <KpiCard label="Initial CAPEX" value={fmtM(tc.total_capex)} />
                    <KpiCard label="Annual OPEX" value={fmtM(opex.total) + '/yr'} />
                    <KpiCard label="Cost / Sat / Year" value={`$${tc.cost_per_sat_per_year.toFixed(2)}M`} />
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
                    <KpiCard label="Constellation" value={`${con.total_satellites} sats`}
                      sub={`${con.num_planes} planes × ${con.sats_per_plane}`} />
                    <KpiCard label="Altitude" value={`${fmt(con.altitude_km, 0)} km`}
                      sub={`${fmt(con.inclination_deg, 1)}° incl`} />
                    <KpiCard label="Orbital period" value={`${fmt(orb.period_min)} min`}
                      sub={`${fmt(orb.orbits_per_day, 1)} orbits/day`} />
                    <KpiCard label="Coverage / Sat" value={`${fmt(cov.coverage_per_sat_pct, 2)}%`}
                      sub={`avg revisit ${fmt(cov.avg_revisit_time_min)} min`} />
                  </div>
                </section>

                {/* ── CAPEX breakdown ──────────────────────────────────────── */}
                <section>
                  <SectionTitle>Initial Investment — CAPEX breakdown</SectionTitle>
                  <div className="flex gap-6 items-start">
                    <DonutChart slices={capexSlices} />
                    <div className="flex-1 space-y-3">
                      <Legend items={capexSlices.map((s, i) => ({ ...s, color: DONUT_COLORS[i] }))} />
                      <div className="pt-2 border-t border-gray-800 flex justify-between text-xs">
                        <span className="text-gray-500">Total CAPEX</span>
                        <span className="text-white font-semibold">{fmtM(capex.total)}</span>
                      </div>
                    </div>
                  </div>
                </section>

                {/* ── OPEX bars ────────────────────────────────────────────── */}
                <section>
                  <SectionTitle>Annual Operating Costs — OPEX</SectionTitle>
                  <BarChart items={opexBars} />
                  <div className="mt-3 flex justify-between text-xs border-t border-gray-800 pt-2">
                    <span className="text-gray-500">Total Annual OPEX</span>
                    <span className="text-white font-semibold">{fmtM(opex.total)}/yr</span>
                  </div>
                </section>

                {/* ── Cumulative cost line ─────────────────────────────────── */}
                <section>
                  <SectionTitle>Cumulative Cost over Mission Life</SectionTitle>
                  <CumulativeCostChart
                    capex={tc.total_capex}
                    annualOpex={opex.total}
                    years={mp.mission_duration_years}
                  />
                  <div className="flex justify-between text-xs mt-1">
                    <span className="text-gray-500">CAPEX: {fmtM(tc.total_capex)}</span>
                    <span className="text-gray-500">
                      OPEX {mp.mission_duration_years}yr: {fmtM(tc.total_opex)}
                    </span>
                    <span className="text-indigo-400 font-semibold">
                      TCO: {fmtM(tc.total_tco)}
                    </span>
                  </div>
                </section>

                {/* ── Infrastructure & Launch ──────────────────────────────── */}
                <section className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                  <div>
                    <SectionTitle>Infrastructure</SectionTitle>
                    <div className="space-y-2 text-sm text-gray-400">
                      <div className="flex justify-between">
                        <span>Platform</span>
                        <span className="text-gray-200">{mp.platform_description}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Satellite mass</span>
                        <span className="text-gray-200">{fmt(mp.satellite_mass_kg, 0)} kg</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Ground stations</span>
                        <span className="text-gray-200">{infra.ground_stations}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Engineering staff</span>
                        <span className="text-gray-200">{infra.engineers} people</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Satellite lifetime</span>
                        <span className="text-gray-200">{fmt(mp.satellite_lifetime_years)} years</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Replacement rate</span>
                        <span className="text-gray-200">{fmt(mp.replacement_rate_per_year)} sats/yr</span>
                      </div>
                    </div>
                  </div>
                  <div>
                    <SectionTitle>Launch configuration</SectionTitle>
                    <div className="space-y-2 text-sm text-gray-400">
                      <div className="flex justify-between">
                        <span>Launch vehicle</span>
                        <span className="text-gray-200 text-right max-w-[180px]">
                          {data.launch_config.launch_vehicle_description}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Batch size</span>
                        <span className="text-gray-200">{data.launch_config.batch_size} sats</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Initial launches</span>
                        <span className="text-gray-200">{data.launch_config.initial_launches}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Steady-state</span>
                        <span className="text-gray-200">
                          {data.launch_config.annual_replacement_launches} launches/yr
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span>Coverage radius/sat</span>
                        <span className="text-gray-200">{fmt(cov.radius_km, 0)} km</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Max gap time</span>
                        <span className="text-gray-200">{fmt(cov.max_gap_time_min)} min</span>
                      </div>
                    </div>
                  </div>
                </section>
              </>
            )
          })()}
        </div>
      </div>
    </div>
  )
}
